"""Setup configuration for the Distributed Chat System."""

from setuptools import setup, find_packages

setup(
    name="distributed-chat-node",
    version="0.1.0",
    description="A distributed peer-to-peer chat system",
    author="DS-G1-SMS Team",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.8",
    install_requires=[
        "grpcio>=1.60.0",
        "grpcio-tools>=1.60.0",
        "protobuf>=4.25.0",
        "websockets>=12.0",
    ],
    entry_points={
        "console_scripts": [
            "chat-node=node.main:main",
            "chat-client=client.main:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
