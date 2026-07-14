import fs from "node:fs";
import path from "node:path";

const sourceRoot = path.resolve(process.argv[2]);
const outputRoot = path.resolve(process.argv[3]);

function stylesFrom(file) {
  const source = fs.readFileSync(file, "utf8");
  return [...source.matchAll(/<style(?:\s[^>]*)?>([\s\S]*?)<\/style>/g)]
    .map((match) => match[1].trim())
    .join("\n\n");
}

function write(relative, content) {
  const target = path.join(outputRoot, relative);
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.writeFileSync(target, `${content.trim()}\n`, "utf8");
}

write("global.css", fs.readFileSync(path.join(sourceRoot, "styles", "global.css"), "utf8"));

const componentFiles = ["Header.astro", "Footer.astro", "Cards.astro", "Icon.astro", "PageHero.astro", "SectionHeader.astro"];
write("components.css", componentFiles.map((name) => stylesFrom(path.join(sourceRoot, "components", name))).join("\n\n"));

const pagesRoot = path.join(sourceRoot, "pages");
for (const entry of fs.readdirSync(pagesRoot, { recursive: true, withFileTypes: true })) {
  if (!entry.isFile() || !entry.name.endsWith(".astro")) continue;
  const file = path.join(entry.parentPath, entry.name);
  const relative = path.relative(pagesRoot, file).replaceAll("\\", "/");
  const outputName = relative.replaceAll("/", "-").replace("[slug]", "detail").replace(/\.astro$/, ".css");
  write(path.join("pages", outputName), stylesFrom(file));
}
