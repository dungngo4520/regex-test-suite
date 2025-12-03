#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

// --- Minimal, focused runner ---

const toChars = (s) => Array.from(s);

const translatePattern = (pattern) => {
    let p = pattern, prev;
    do {
        prev = p;
        p = p
            .replace(/@\[unicode:([0-9A-Fa-f]{4,6})\]/g, (_, code) =>
                code.length <= 4 ? `\\u${code.padStart(4, '0')}` : `\\u{${code}}`
            )
            .replace(/@\[hex:([0-9A-Fa-f]{2})\]/g, '\\x$1')
            .replace(/@\[octal:([0-7]{1,3})\]/g, '\\$1')
            .replace(/@\[control:([A-Z])\]/g, '\\c$1')
            .replace(/@\[named:(\w+),(.+?)\]/g, '(?<$1>$2)')
            .replace(/@\[backref:(\w+)\]/g, '\\k<$1>');
    } while (p !== prev);
    return p;
};

const translateData = (s) => {
    let t = s, prev;
    do {
        prev = t;
        t = t
            .replace(/@\[unicode:([0-9A-Fa-f]{4,6})\]/g, (_, code) => String.fromCodePoint(parseInt(code, 16)))
            .replace(/@\[hex:([0-9A-Fa-f]{2})\]/g, (_, h) => String.fromCharCode(parseInt(h, 16)))
            .replace(/@\[octal:([0-7]{1,3})\]/g, (_, o) => String.fromCharCode(parseInt(o, 8)))
            .replace(/@\[control:([A-Z])\]/g, (_, c) => String.fromCharCode(c.charCodeAt(0) - 64));
    } while (t !== prev);
    return t;
};

const compile = (pattern, flags) => {
    try { return new RegExp(translatePattern(pattern), flags || ''); }
    catch { return null; }
};

const execAll = (re, input, isGlobal) => {
    const out = [];
    if (isGlobal) {
        re.lastIndex = 0; let m;
        while ((m = re.exec(input)) !== null) {
            out.push(m);
            if (m.index === re.lastIndex) re.lastIndex++;
        }
    } else {
        const m = re.exec(input); if (m) out.push(m);
    }
    return out;
};

const compare = (m, exp) => {
    const input = m.input;
    const start = toChars(input.slice(0, m.index)).length;
    const end = start + toChars(m[0]).length;
    if (start !== exp.start) return `Start mismatch: expected ${exp.start}, got ${start}`;
    if (end !== exp.end) return `End mismatch: expected ${exp.end}, got ${end}`;
    if (m[0] !== exp.match) return `Text mismatch: expected '${exp.match}', got '${m[0]}'`;
    if (exp.groups !== undefined) {
        const g = m.slice(1);
        if (g.length !== exp.groups.length) return `Group count mismatch: expected ${exp.groups.length}, got ${g.length}`;
        for (let i = 0; i < exp.groups.length; i++) {
            const a = g[i] === undefined ? null : g[i];
            if (a !== exp.groups[i]) return `Group ${i + 1} mismatch: expected '${exp.groups[i]}', got '${a}'`;
        }
    }
    return null;
};

const runCase = (caseDef, test, stats) => {
    stats.total++;
    const re = compile(caseDef.pattern, caseDef.flags);
    const input = translateData(test.input);
    const expected = test.matches.map(m => ({ ...m, match: translateData(m.match) }));
    if (!re) {
        if (expected.length === 0) { stats.passed++; return; }
        stats.failed++; throw new Error('Failed to compile pattern');
    }
    const matches = execAll(re, input, (caseDef.flags || '').includes('g'));
    if (matches.length !== expected.length) {
        stats.failed++; throw new Error(`Match count mismatch: expected ${expected.length}, got ${matches.length}`);
    }
    for (let i = 0; i < matches.length; i++) {
        const err = compare(matches[i], expected[i]);
        if (err) { stats.failed++; throw new Error(`Match ${i}: ${err}`); }
    }
    stats.passed++;
};

const runFile = (filePath, stats, verbose = false) => {
    const cases = JSON.parse(fs.readFileSync(filePath, 'utf8'));
    let ok = true;
    for (const c of cases) {
        for (const t of c.tests) {
            try { runCase(c, t, stats); if (verbose) console.log(`    OK ${t.description}`); }
            catch (e) { ok = false; if (verbose) console.log(`    FAILED ${t.description}\n      ${e.message}`); }
        }
    }
    return ok;
};

const findJson = (dir) => {
    const out = [];
    const walk = (d) => {
        for (const entry of fs.readdirSync(d, { withFileTypes: true })) {
            const p = path.join(d, entry.name);
            if (entry.isDirectory()) walk(p);
            else if (entry.isFile() && entry.name.endsWith('.json')) out.push(p);
        }
    };
    walk(dir);
    return out.sort();
};

function main() {
    const args = process.argv.slice(2);
    let verbose = false, single = null;
    for (let i = 0; i < args.length; i++) {
        if (args[i] === '-v' || args[i] === '--verbose') verbose = true;
        else if (args[i] === '-f' || args[i] === '--file') { single = args[i + 1]; i++; }
        else if (args[i] === '-h' || args[i] === '--help') {
            console.log('Usage: run_tests.js [-v] [-f <path>]');
            return 0;
        }
    }

    const repoRoot = path.dirname(__dirname);
    const testsDir = path.join(repoRoot, 'tests');
    if (!fs.existsSync(testsDir)) { console.error(`Error: Tests directory not found: ${testsDir}`); return 1; }

    const stats = { total: 0, passed: 0, failed: 0 };

    if (single) {
        const file = path.join(repoRoot, single);
        if (!fs.existsSync(file)) { console.error(`Error: File not found: ${file}`); return 1; }
        console.log(`Running tests from ${path.basename(file)}`);
        console.log('='.repeat(70));
        const ok = runFile(file, stats, true);
        console.log('\n' + '='.repeat(70));
        console.log(`Total: ${stats.total} tests`);
        console.log(`Passed: ${stats.passed}`);
        console.log(`Failed: ${stats.failed}`);
        return ok ? 0 : 1;
    }

    const files = findJson(testsDir);
    const repo = path.dirname(testsDir);
    console.log('Running Regex Test Suite');
    console.log(`Found ${files.length} test files`);
    console.log();
    let filesOk = 0;
    for (const f of files) {
        const rel = path.relative(repo, f);
        console.log(rel);
        const ok = runFile(f, stats, verbose);
        if (ok) { filesOk++; if (!verbose) console.log('All tests passed'); }
        else if (!verbose) console.log('Some tests failed');
        console.log();
    }
    console.log(`Total Tests: ${stats.total}`);
    console.log(`Passed: ${stats.passed} (${((100 * stats.passed) / stats.total).toFixed(1)}%)`);
    console.log(`Failed: ${stats.failed}`);
    console.log(`Files: ${filesOk}/${files.length} passed`);
    return stats.failed === 0 ? 0 : 1;
}

process.exit(main());
