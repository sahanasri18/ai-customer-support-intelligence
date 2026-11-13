import { readdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';
import { compile } from 'tailwindcss';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const sourceRoot = path.join(root, 'src');
const classTokens = new Set();

async function collect(dir) {
  for (const entry of await readdir(dir, { withFileTypes: true })) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) await collect(fullPath);
    else if (/\.(tsx?|jsx?)$/.test(entry.name)) {
      const source = await readFile(fullPath, 'utf8');
      // Match one quote type at a time. A broad character-class delimiter can
      // pair a JSX double quote with an apostrophe inside an adjacent string,
      // skipping utility classes and leaving pages only partially styled.
      const stringLiteral = /"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|`(?:\\.|[^`\\])*`/g;
      for (const match of source.matchAll(stringLiteral)) {
        const literal = match[0].slice(1, -1);
        for (const token of literal.split(/\s+/)) {
          if (/^[\w!:/.[\]%-]+$/.test(token)) classTokens.add(token);
        }
      }
    }
  }
}

await collect(sourceRoot);
const require = createRequire(import.meta.url);
const compiler = await compile('@import "tailwindcss";', {
  base: root,
  loadStylesheet: async (id, base) => {
    const resolved = id === 'tailwindcss'
      ? require.resolve('tailwindcss/index.css')
      : path.resolve(base, id);
    return { path: resolved, base: path.dirname(resolved), content: await readFile(resolved, 'utf8') };
  },
});
const css = compiler.build([...classTokens]);
await writeFile(path.join(sourceRoot, 'tailwind.generated.css'), css, 'utf8');
console.log(`Generated Tailwind CSS for ${classTokens.size} source tokens.`);
