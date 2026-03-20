from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="trade-document-ocr",
    version="0.1.0",
    author="Shahin Hasanov",
    author_email="",
    description="OCR and structured data extraction for customs trade documents",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/shahinhasanov/trade-document-ocr",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.9",
    install_requires=requirements,
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering :: Image Recognition",
        "Topic :: Office/Business :: Financial",
    ],
    entry_points={
        "console_scripts": [
            "trade-ocr=ocr.pipeline:main",
        ],
    },
)
