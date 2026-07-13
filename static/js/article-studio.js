(() => {
  const byId = (id) => document.getElementById(id);
  const fields = {
    select: byId("article-select"), title: byId("title"), slug: byId("slug"), category: byId("category"),
    author: byId("author"), date: byId("date"), lead: byId("lead"), body: byId("body"),
    hero: byId("hero-image"), source: byId("source-file")
  };
  if (!fields.title) return;
  if (!fields.date.value) fields.date.value = new Date().toISOString().slice(0, 10);

  byId("load-article")?.addEventListener("click", () => {
    const slug = fields.select.value;
    window.location.href = slug ? `/article-studio/?slug=${encodeURIComponent(slug)}` : "/article-studio/";
  });

  const preview = () => {
    byId("preview-title").textContent = fields.title.value || "新文章標題";
    byId("preview-category").textContent = fields.category.value;
    byId("preview-author").textContent = fields.author.value || "CAIM";
    byId("preview-date").textContent = fields.date.value;
    byId("preview-lead").textContent = fields.lead.value;
    const body = byId("preview-body");
    body.replaceChildren(...fields.body.value.split(/\n\s*\n/).filter(Boolean).map((text) => {
      const paragraph = document.createElement("p");
      paragraph.textContent = text.trim();
      return paragraph;
    }));
  };
  [fields.title, fields.category, fields.author, fields.date, fields.lead, fields.body].forEach((field) => field.addEventListener("input", preview));
  fields.title.addEventListener("input", () => {
    if (fields.slug.dataset.edited) return;
    fields.slug.value = fields.title.value.toLowerCase().trim().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  });
  fields.slug.addEventListener("input", () => { fields.slug.dataset.edited = "true"; });
  fields.hero.addEventListener("change", () => {
    const file = fields.hero.files[0];
    if (file) byId("preview-image").src = URL.createObjectURL(file);
  });
  byId("remove-image")?.addEventListener("click", () => {
    byId("remove-image-value").value = "1";
    fields.hero.value = "";
    byId("preview-image").src = "/static/assets/hero-asian-creative-team.jpg";
    byId("remove-image").textContent = "圖片將在儲存時移除";
    byId("remove-image").disabled = true;
  });
  fields.source.addEventListener("change", async () => {
    const file = fields.source.files[0];
    if (file && /\.(md|txt)$/i.test(file.name)) {
      fields.body.value = await file.text();
      preview();
    }
  });
  preview();
})();
