from openai import AsyncOpenAI

from config import Settings


class AIService:
    def __init__(self, settings: Settings):
        client_options = {"api_key": settings.openai_api_key}
        if settings.openai_base_url:
            client_options["base_url"] = settings.openai_base_url
        self.client = AsyncOpenAI(**client_options)
        self.settings = settings

    async def answer(self, question: str, context: list[dict[str, str]], language: str = "fr") -> str:
        language_names = {
            "en": "English",
            "fr": "French",
            "es": "Spanish",
            "it": "Italian",
            "de": "German",
            "ru": "Russian",
        }
        response_language = language_names.get(language, "French")
        messages = [
            {
                "role": "system",
                "content": (
                    f"Tu es Husey Ai, un assistant Discord précis, utile et naturel. Réponds en {response_language}. "
                    "Structure les réponses longues en sections, "
                    "et ne prétends pas avoir accès à des informations que tu n'as pas."
                ),
            },
            *context,
            {"role": "user", "content": question},
        ]
        response = await self.client.chat.completions.create(
            model=self.settings.ai_model,
            messages=messages,
            max_tokens=self.settings.ai_max_tokens,
            temperature=self.settings.ai_temperature,
        )
        return response.choices[0].message.content or "Je n'ai pas pu formuler de réponse."

    async def generate_image(self, prompt: str) -> str:
        response = await self.client.images.generate(
            model=self.settings.ai_image_model,
            prompt=prompt,
            size="1024x1024",
            quality="auto",
        )
        if not response.data or not response.data[0].url:
            raise RuntimeError("Le fournisseur IA n'a pas renvoyé d'image.")
        return response.data[0].url
