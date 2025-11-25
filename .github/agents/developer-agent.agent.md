---
# Fill in the fields below to create a basic custom agent for your repository.
# The Copilot CLI can be used for local testing: https://gh.io/customagents/cli
# To make this agent available, merge this file into the default repository branch.
# For format details, see: https://gh.io/customagents/config

name: 'developer-agent'
description: 'Used for development on the P2P chat service project. Can use Makefile to access dev tools.'
---

# My Agent

Other than developing as given instructions, agent shall run 'make format' to make sure code is formatted and 'make lint' to check the linting of the code.
