import { pathToFileURL } from "node:url";
import path from "node:path";

const root = path.resolve(process.argv[2] || "../caim-website-francis-v2");
const load = (relativePath) => import(pathToFileURL(path.join(root, relativePath)).href);

const [content, pages, site, news] = await Promise.all([
  load("src/data/content.ts"),
  load("src/data/pages.ts"),
  load("src/data/site.ts"),
  load("src/data/news.ts")
]);

process.stdout.write(JSON.stringify({
  content: Object.fromEntries(Object.entries(content)),
  pages: pages.pages,
  site: site.site,
  navigation: site.navigation,
  seoTitles: site.seoTitles,
  newsItems: news.newsItems
}));
