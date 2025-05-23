from setuptools import setup, find_packages

setup(
    name="crypto-monitor",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "aiogram>=3.0.0",
        "fastapi>=0.109.2",
        "uvicorn>=0.27.1",
        "python-dotenv>=1.0.1",
        "httpx>=0.24.0",
        "openai>=1.0.0",
        "apscheduler>=3.10.4",
        "pydantic>=2.1.1,<3.0.0",
        "python-jose>=3.3.0",
        "supabase>=1.0.0",
        "python-multipart>=0.0.6",
        "aiohttp>=3.9.0",
        "tenacity>=8.2.0",
        "sqlalchemy>=2.0.0"
    ],
    python_requires=">=3.12",
) 