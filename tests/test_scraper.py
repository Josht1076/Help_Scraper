import unittest

import scraper


class ScraperUnitTests(unittest.TestCase):
    def test_slugify_url(self):
        slug = scraper.slugify_url("https://docs.example.com/guide/start?lang=en")
        self.assertEqual(slug, "docs.example.com-guide-start-lang-en")

    def test_parse_page_extracts_markdown_and_links(self):
        html_doc = """
        <html>
            <head><title>Docs Title</title></head>
            <body>
                <h1>Heading</h1>
                <p>See <a href='/next'>next page</a>.</p>
                <pre><code>pip install thing</code></pre>
            </body>
        </html>
        """
        page = scraper.parse_page(html_doc, "https://example.com/start", toc_keywords=["toc"])
        self.assertEqual(page.title, "Docs Title")
        self.assertIn("# Heading", page.markdown)
        self.assertIn("[next page](/next)", page.markdown)
        self.assertIn("```", page.markdown)
        self.assertIn("https://example.com/next", page.links)

    def test_parse_page_extracts_toc_links(self):
        html_doc = """
        <html><body>
            <nav class='table-of-contents'>
                <a href='/user-guide/a.html'>A</a>
                <a href='/user-guide/b.html'>B</a>
            </nav>
            <a href='/other.html'>Other</a>
        </body></html>
        """
        page = scraper.parse_page(html_doc, "https://www.advancedinstaller.com/user-guide/", toc_keywords=["table-of-contents"])
        self.assertIn("https://www.advancedinstaller.com/user-guide/a.html", page.toc_links)
        self.assertIn("https://www.advancedinstaller.com/user-guide/b.html", page.toc_links)
        self.assertNotIn("https://www.advancedinstaller.com/other.html", page.toc_links)

    def test_should_visit_respects_domain_and_prefix(self):
        self.assertTrue(
            scraper.should_visit(
                "https://www.advancedinstaller.com/user-guide/intro.html",
                {"www.advancedinstaller.com"},
                ["https://www.advancedinstaller.com/user-guide/"],
            )
        )
        self.assertFalse(
            scraper.should_visit(
                "https://www.advancedinstaller.com/blog/",
                {"www.advancedinstaller.com"},
                ["https://www.advancedinstaller.com/user-guide/"],
            )
        )


if __name__ == "__main__":
    unittest.main()
