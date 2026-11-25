import unittest
from main import parse_page_ranges


class TestPageParser(unittest.TestCase):
    def test_single_pages(self):
        pages, err = parse_page_ranges("1, 3, 5", max_pages=10)
        self.assertEqual(err, "")
        self.assertEqual(pages, [0, 2, 4])

    def test_ranges(self):
        pages, err = parse_page_ranges("2-5", max_pages=10)
        self.assertEqual(err, "")
        self.assertEqual(pages, [1, 2, 3, 4])

        pages_tilde, err_tilde = parse_page_ranges("2~4", max_pages=10)
        self.assertEqual(err_tilde, "")
        self.assertEqual(pages_tilde, [1, 2, 3])

    def test_mixed_expression(self):
        pages, err = parse_page_ranges("1, 3, 5-7, 10", max_pages=10)
        self.assertEqual(err, "")
        self.assertEqual(pages, [0, 2, 4, 5, 6, 9])

    def test_deduplication_and_sorting(self):
        # 중복 페이지는 제거되고 오름차순 정렬되어야 함
        pages, err = parse_page_ranges("5, 1, 3, 1-3", max_pages=10)
        self.assertEqual(err, "")
        self.assertEqual(pages, [0, 1, 2, 4])

    def test_whitespace_and_semicolons(self):
        pages, err = parse_page_ranges(" 1 ;  3 - 5 ; 8 ", max_pages=10)
        self.assertEqual(err, "")
        self.assertEqual(pages, [0, 2, 3, 4, 7])

    def test_out_of_bounds(self):
        pages, err = parse_page_ranges("12", max_pages=10)
        self.assertNotEqual(err, "")
        self.assertEqual(pages, [])

        pages, err = parse_page_ranges("0", max_pages=10)
        self.assertNotEqual(err, "")
        self.assertEqual(pages, [])

        pages, err = parse_page_ranges("5-15", max_pages=10)
        self.assertNotEqual(err, "")
        self.assertEqual(pages, [])

    def test_invalid_syntax(self):
        pages, err = parse_page_ranges("abc", max_pages=10)
        self.assertNotEqual(err, "")
        self.assertEqual(pages, [])

        pages, err = parse_page_ranges("5-3", max_pages=10)
        self.assertNotEqual(err, "")
        self.assertEqual(pages, [])

        pages, err = parse_page_ranges("", max_pages=10)
        self.assertNotEqual(err, "")
        self.assertEqual(pages, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
