import html2text
from playwright.async_api import async_playwright, Page, BrowserContext

class PlaywrightManager:
    _instance = None

    @classmethod
    async def get_instance(cls) -> 'PlaywrightManager':
        if cls._instance is None:
            cls._instance = PlaywrightManager()
            await cls._instance.start()
        return cls._instance

    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context: BrowserContext = None
        self.page: Page = None
        self.html2text_converter = html2text.HTML2Text()
        self.html2text_converter.ignore_links = False
        self.html2text_converter.ignore_images = False

    async def start(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()

    async def execute_action(self, command: str, target: str) -> dict:
        try:
            if command == 'goto':
                await self.page.goto(target, wait_until='networkidle')
            elif command == 'click':
                await self.page.click(target)
                await self.page.wait_for_load_state('networkidle')
            elif command == 'type':
                parts = target.split('|', 1)
                if len(parts) == 2:
                    await self.page.fill(parts[0], parts[1])
                else:
                    return {'error': "Invalid type format. Use 'selector|text'", 'exit_code': 1}
            else:
                return {'error': f"Unknown browser command: {command}", 'exit_code': 1}

            html = await self.page.content()
            markdown_content = self.html2text_converter.handle(html)
            
            return {
                'output': f"Successfully executed '{command}'.\nCurrent URL: {self.page.url}",
                'content': markdown_content,
                'exit_code': 0
            }

        except Exception as e:
            return {'error': f"Browser error: {str(e)}", 'exit_code': 1}

    async def close(self):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        PlaywrightManager._instance = None
