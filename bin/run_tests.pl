#!/usr/bin/env perl

use strict;
use warnings;
use JSON::PP qw(decode_json);
use File::Find;
use File::Spec;
use File::Basename;
use Getopt::Long;

package TestResult {
    sub new {
        my ($class, $passed, $message) = @_;
        my $self = {
            passed => $passed,
            message => $message // ''
        };
        return bless $self, $class;
    }
}

package RegexTestRunner {
    sub new {
        my ($class) = @_;
        my $self = {
            total_tests => 0,
            passed_tests => 0,
            failed_tests => 0,
            skipped_tests => 0
        };
        return bless $self, $class;
    }

    sub translate_pattern {
        my ($self, $pattern) = @_;

        # Translate generic annotations to Perl-specific syntax
        # Process innermost annotations first for nested cases
        my $changed = 1;
        do {
            my $before = $pattern;

            $pattern =~ s/@\[unicode:([0-9A-Fa-f]{4,6})\]/\\x{$1}/g;
            $pattern =~ s/@\[hex:([0-9A-Fa-f]{2})\]/\\x$1/g;
            $pattern =~ s/@\[octal:([0-7]{1,3})\]/\\$1/g;
            $pattern =~ s/@\[control:([A-Z])\]/\\c$1/g;
            $pattern =~ s/@\[named:(\w+),(.+?)\]/(?<$1>$2)/g;
            $pattern =~ s/@\[backref:(\w+)\]/\\k<$1>/g;

            $changed = ($before ne $pattern);
        } while ($changed);

        return $pattern;
    }

    sub translate_test_data {
        my ($self, $str) = @_;

        # Translate annotations in test data to actual character values
        my $changed = 1;
        do {
            my $before = $str;

            $str =~ s/@\[unicode:([0-9A-Fa-f]{4,6})\]/chr(hex($1))/eg;
            $str =~ s/@\[hex:([0-9A-Fa-f]{2})\]/chr(hex($1))/eg;
            $str =~ s/@\[octal:([0-7]{1,3})\]/chr(oct($1))/eg;
            $str =~ s/@\[control:([A-Z])\]/chr(ord($1) - 64)/eg;

            $changed = ($before ne $str);
        } while ($changed);

        return $str;
    }

    sub compile_pattern {
        my ($self, $pattern, $flags) = @_;

        # Translate pattern first
        $pattern = $self->translate_pattern($pattern);

        # Build regex modifier string
        my $modifiers = '';
        $modifiers .= 'i' if $flags =~ /i/;
        $modifiers .= 'm' if $flags =~ /m/;
        $modifiers .= 's' if $flags =~ /s/;
        $modifiers .= 'x' if $flags =~ /x/;

        # Try to compile the pattern
        my $regex;
        eval {
            if ($modifiers) {
                $regex = qr/(?$modifiers)$pattern/;
            } else {
                $regex = qr/$pattern/;
            }
        };

        return $@ ? undef : $regex;
    }

    sub count_capturing_groups {
        my ($self, $pattern) = @_;
        my $count = 0;
        my $i = 0;
        my $len = length($pattern);

        while ($i < $len) {
            my $char = substr($pattern, $i, 1);

            if ($char eq '\\') {
                $i += 2; # Skip escaped character
                next;
            }

            if ($char eq '(' && $i + 1 < $len) {
                my $next = substr($pattern, $i + 1, 1);
                # Check if it's a non-capturing group (?:...) or other special group
                if ($next eq '?') {
                    my $after = substr($pattern, $i + 2, 1);
                    # Check for (?< which could be lookbehind or named group
                    if ($after eq '<') {
                        my $third = $i + 3 < $len ? substr($pattern, $i + 3, 1) : '';
                        # (?<=...) or (?<!...) are lookbehinds (non-capturing)
                        if ($third eq '=' || $third eq '!') {
                            # Non-capturing lookbehind, skip
                        } else {
                            # Named group (?<name>...) - capturing
                            $count++;
                        }
                    }
                    # Named group with (?'name'...) - capturing
                    elsif ($after eq "'") {
                        $count++;
                    }
                    # (?:...) (?=...) (?!...) (?>...) are non-capturing
                    elsif ($after =~ /[:=!>]/) {
                        # Non-capturing group, skip
                    }
                } else {
                    # Regular capturing group
                    $count++;
                }
            }

            $i++;
        }

        return $count;
    }

    sub find_matches {
        my ($self, $regex, $input_str, $global_flag, $pattern_str) = @_;
        my @matches;
        my $group_count = $self->count_capturing_groups($pattern_str);

        if ($global_flag) {
            while ($input_str =~ /$regex/g) {
                my $match_str = $&;
                my $start = $-[0];
                my $end = $+[0];

                # Collect all captured groups including undefined ones
                my @groups;
                for (my $i = 1; $i <= $group_count; $i++) {
                    no strict 'refs';
                    push @groups, $$i;
                }

                push @matches, {
                    match => $match_str,
                    start => $start,
                    end => $end,
                    groups => \@groups
                };
            }
        } else {
            if ($input_str =~ /$regex/) {
                my $match_str = $&;
                my $start = $-[0];
                my $end = $+[0];

                # Collect all captured groups including undefined ones
                my @groups;
                for (my $i = 1; $i <= $group_count; $i++) {
                    no strict 'refs';
                    push @groups, $$i;
                }

                push @matches, {
                    match => $match_str,
                    start => $start,
                    end => $end,
                    groups => \@groups
                };
            }
        }

        return \@matches;
    }

    sub compare_match {
        my ($self, $actual, $expected) = @_;

        if ($actual->{start} != $expected->{start}) {
            return TestResult->new(0,
                "Start position mismatch: expected $expected->{start}, got $actual->{start}");
        }

        if ($actual->{end} != $expected->{end}) {
            return TestResult->new(0,
                "End position mismatch: expected $expected->{end}, got $actual->{end}");
        }

        if ($actual->{match} ne $expected->{match}) {
            return TestResult->new(0,
                "Match text mismatch: expected '$expected->{match}', got '$actual->{match}'");
        }

        if (exists $expected->{groups}) {
            my $expected_groups = $expected->{groups};
            my $actual_groups = $actual->{groups};

            if (scalar(@$actual_groups) != scalar(@$expected_groups)) {
                return TestResult->new(0,
                    "Group count mismatch: expected " . scalar(@$expected_groups) .
                    ", got " . scalar(@$actual_groups));
            }

            for (my $i = 0; $i < scalar(@$expected_groups); $i++) {
                my $exp_val = $expected_groups->[$i];
                my $act_val = $actual_groups->[$i];

                # Handle null/undef comparison
                if (!defined($exp_val) && !defined($act_val)) {
                    next;
                }
                if (!defined($exp_val) || !defined($act_val) || $exp_val ne $act_val) {
                    $exp_val //= 'null';
                    $act_val //= 'null';
                    return TestResult->new(0,
                        "Group " . ($i + 1) . " mismatch: expected '$exp_val', got '$act_val'");
                }
            }
        }

        return TestResult->new(1);
    }

    sub run_test {
        my ($self, $test_case, $test) = @_;
        $self->{total_tests}++;

        my $pattern_str = $test_case->{pattern};
        my $flags = $test_case->{flags} // '';
        my $input_str = $self->translate_test_data($test->{input});

        # Translate expected match values
        my $expected_matches = [];
        foreach my $expected (@{$test->{matches}}) {
            my %translated = %$expected;
            $translated{match} = $self->translate_test_data($expected->{match});
            push @$expected_matches, \%translated;
        }

        # Translate pattern for group counting
        my $translated_pattern = $self->translate_pattern($pattern_str);

        my $pattern = $self->compile_pattern($pattern_str, $flags);

        if (!defined $pattern) {
            if (scalar(@$expected_matches) == 0) {
                $self->{passed_tests}++;
                return TestResult->new(1, 'Invalid pattern correctly rejected');
            } else {
                $self->{failed_tests}++;
                return TestResult->new(0, 'Failed to compile pattern');
            }
        }

        my $global_flag = $flags =~ /g/;
        my $actual_matches = $self->find_matches($pattern, $input_str, $global_flag, $translated_pattern);

        if (scalar(@$actual_matches) != scalar(@$expected_matches)) {
            $self->{failed_tests}++;
            return TestResult->new(0,
                "Match count mismatch: expected " . scalar(@$expected_matches) .
                ", got " . scalar(@$actual_matches));
        }

        for (my $i = 0; $i < scalar(@$actual_matches); $i++) {
            my $result = $self->compare_match($actual_matches->[$i], $expected_matches->[$i]);
            if (!$result->{passed}) {
                $self->{failed_tests}++;
                return TestResult->new(0, "Match $i: " . $result->{message});
            }
        }

        $self->{passed_tests}++;
        return TestResult->new(1);
    }

    sub run_test_file {
        my ($self, $file_path, $verbose) = @_;

        open my $fh, '<', $file_path or die "Cannot open $file_path: $!";
        my $content = do { local $/; <$fh> };
        close $fh;

        my $test_cases = JSON::PP::decode_json($content);
        my $file_passed = 1;

        foreach my $test_case (@$test_cases) {
            if ($verbose) {
                print "  $test_case->{description}\n";
            }

            foreach my $test (@{$test_case->{tests}}) {
                my $result = $self->run_test($test_case, $test);

                if ($verbose) {
                    my $status = $result->{passed} ? 'OK' : 'FAILED';
                    print "    $status $test->{description}\n";
                    if (!$result->{passed}) {
                        print "      $result->{message}\n";
                    }
                }

                if (!$result->{passed}) {
                    $file_passed = 0;
                }
            }
        }

        return $file_passed;
    }

    sub run_suite {
        my ($self, $tests_dir, $verbose) = @_;

        my @test_files;
        File::Find::find(sub {
            push @test_files, $File::Find::name if /\.json$/;
        }, $tests_dir);
        @test_files = sort @test_files;

        my $repo_root = File::Basename::dirname($tests_dir);

        print "Running Regex Test Suite\n";
        print "Found " . scalar(@test_files) . " test files\n";
        print "\n";

        my $passed_files = 0;
        my $failed_files = 0;

        foreach my $test_file (@test_files) {
            my $relative_path = File::Spec->abs2rel($test_file, $repo_root);
            print "$relative_path\n";

            my $file_passed = $self->run_test_file($test_file, $verbose);

            if ($file_passed) {
                $passed_files++;
                print "All tests passed\n" unless $verbose;
            } else {
                $failed_files++;
                print "Some tests failed\n" unless $verbose;
            }

            print "\n";
        }

        print "Total Tests: $self->{total_tests}\n";
        my $pass_pct = sprintf("%.1f", 100 * $self->{passed_tests} / $self->{total_tests});
        print "Passed: $self->{passed_tests} ($pass_pct%)\n";
        print "Failed: $self->{failed_tests}\n";
        print "Files: $passed_files/" . scalar(@test_files) . " passed\n";

        return $self->{failed_tests} == 0;
    }
}

sub main {
    my $verbose = 0;
    my $specific_file;
    my $help = 0;

    GetOptions(
        'verbose|v' => \$verbose,
        'file|f=s' => \$specific_file,
        'help|h' => \$help
    ) or die "Error in command line arguments\n";

    if ($help) {
        print "Usage: run_tests.pl [options]\n";
        print "\n";
        print "Options:\n";
        print "  -v, --verbose    Show detailed output for each test\n";
        print "  -f, --file PATH  Run tests from a specific file\n";
        print "  -h, --help       Show this help message\n";
        return 0;
    }

    # Get paths
    my $script_dir = dirname(File::Spec->rel2abs($0));
    my $repo_root = dirname($script_dir);
    my $tests_dir = File::Spec->catdir($repo_root, 'tests');

    if (!-d $tests_dir) {
        print STDERR "Error: Tests directory not found: $tests_dir\n";
        return 1;
    }

    my $runner = RegexTestRunner->new();

    if (defined $specific_file) {
        # Run single file
        my $test_file = File::Spec->catfile($repo_root, $specific_file);
        if (!-f $test_file) {
            print STDERR "Error: File not found: $test_file\n";
            return 1;
        }

        print "Running tests from " . basename($test_file) . "\n";
        print "=" x 70 . "\n";
        print "\n";

        my $success = $runner->run_test_file($test_file, 1);

        print "\n";
        print "=" x 70 . "\n";
        print "Total: $runner->{total_tests} tests\n";
        print "Passed: $runner->{passed_tests}\n";
        print "Failed: $runner->{failed_tests}\n";

        return $success ? 0 : 1;
    } else {
        # Run full suite
        my $success = $runner->run_suite($tests_dir, $verbose);
        return $success ? 0 : 1;
    }
}

exit main();
