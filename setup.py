from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith('#')]

setup(
    name="labxtract",
    version="1.0.0",
    author="liamsdat",
    author_email="liamsdat@icloud.com",
    description="Парсер лабораторных анализов из Excel файлов",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="None",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Healthcare Industry",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Scientific/Engineering :: Medical Science Apps.",
        "Topic :: Text Processing :: Filters",
        "Topic :: Utilities",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "labxtract=labxtract.cli:cli",
        ],
    },
    include_package_data=True,
)