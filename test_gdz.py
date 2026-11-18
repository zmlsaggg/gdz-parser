import unittest
from gdz import rank, search_links


class ParserTests(unittest.TestCase):
    def test_links(self):
        self.assertEqual(list(search_links([
            '/url?q=https%3A%2F%2Fexample.org%2F215%23top',
            'https://example.org/215', 'javascript:void(0)',
            'https://www.google.com/search?q=gdz',
        ])), ['https://example.org/215'])

    def test_page_number_and_paywall(self):
        query = 'Математика 10 класс Максимов 215 страница'
        self.assertGreater(rank(query, 'Максимов — страница 215', '', 1), 0)
        self.assertEqual(rank(query, 'Максимов — страница 216', '', 1), 0)
        self.assertEqual(rank(query, 'Максимов — страница 215', 'Оплатите подписку', 1), 0)



class UploadTests(unittest.IsolatedAsyncioTestCase):
    async def test_upload(self):
        from unittest.mock import AsyncMock
        from gdz import upload_kappa, KAPPA_UPLOAD

        request = AsyncMock()
        response = request.post.return_value
        response.ok = True
        response.json.return_value = {'link': 'https://kappa.lol/abc', 'ext': '.png'}
        self.assertEqual(await upload_kappa(request, b'png'), 'https://kappa.lol/abc.png')
        self.assertEqual(request.post.call_args.args, (KAPPA_UPLOAD,))
        self.assertEqual(request.post.call_args.kwargs['multipart']['file']['buffer'], b'png')
        response.dispose.assert_awaited_once()
