// Rebuild locally with: bun install --frozen-lockfile && bun run build
import { readdirSync, readFileSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'

const root = import.meta.dir
const result = await Bun.build({
  entrypoints: [join(root, 'server.ts')], target: 'bun',
  minify: true, sourcemap: 'none', packages: 'bundle',
})
if (!result.success) throw new Error(result.logs.join('\n'))
await Bun.write(join(root, 'server.bundle.js'), result.outputs[0])
// Retain the complete notices of the locked dependency closure, including
// dependencies tree-shaken out of the runtime bundle. Never copy account data.
const modules = join(root, 'node_modules')
const packages = readdirSync(modules).filter(n => !n.startsWith('.')).flatMap(n =>
  n.startsWith('@') ? readdirSync(join(modules, n)).map(p => `${n}/${p}`) : [n])
const notices = ['# Third-party notices', '',
  'Owned source is MIT. The bundled npm dependencies retain their original terms.',
  'Generated from the package-local frozen lockfile; includes the full installed dependency closure.', '']
for (const name of packages.sort()) {
  const dir = join(modules, name)
  const pkg = JSON.parse(readFileSync(join(dir, 'package.json'), 'utf8'))
  const licenses = readdirSync(dir).filter(n => /^(licen[sc]e|copying|notice)([.\-]|$)/i.test(n)).sort()
  if (!licenses.length) throw new Error(`Missing license text: ${name}`)
  notices.push(`## ${name}@${pkg.version} (${pkg.license ?? 'see terms'})`, '')
  for (const file of licenses) notices.push(`### ${file}`, '', readFileSync(join(dir, file), 'utf8').trim(), '')
}
writeFileSync(join(root, 'THIRD_PARTY_NOTICES.md'), notices.join('\n'))
