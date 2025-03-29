# Echidna MCP Server

This project provides a Model Context Protocol (MCP) server that exposes Echidna's smart contract fuzzing capabilities to Large Language Models.

## Features

- Run Echidna tests on Solidity contracts
- Create and manage Echidna configuration files
- Generate and analyze corpus data
- Filter functions for targeted fuzzing
- Set up end-to-end testing with Etheno

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/echidna-mcp.git
cd echidna-mcp

# Install dependencies
pip install -e .
```

Make sure you have Echidna and Etheno installed separately:

```bash
# Install Echidna (see https://github.com/crytic/echidna for more details)
# Example for Ubuntu:
wget https://github.com/crytic/echidna/releases/download/v2.1.0/echidna-2.1.0-Ubuntu-22.04.tar.gz
tar -xvf echidna-2.1.0-Ubuntu-22.04.tar.gz
sudo mv echidna /usr/local/bin/

# Install Etheno
uv add etheno
```

## Usage

### Starting the Server

```bash
python server.py
```

### Available Tools

The server exposes the following tools:

1. `run_echidna_test` - Run Echidna on a Solidity contract
2. `create_echidna_config` - Create an Echidna configuration file
3. `create_solidity_contract` - Create a Solidity file with provided code
4. `analyze_corpus` - Analyze an Echidna corpus directory
5. `filter_functions` - Create a config to filter functions for testing
6. `setup_end_to_end_test` - Set up end-to-end testing with Etheno

### Example Workflow

1. Create a Solidity contract with Echidna properties
2. Create an Echidna configuration file
3. Run Echidna tests
4. Analyze the results

## Resources

The server provides access to Echidna documentation via the `resource://echidna-features` resource.

## Requirements

- Python 3.12+
- Echidna
- Etheno
- Model Context Protocol (MCP) SDK