import os
import json
import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Union, Any

from mcp.server.fastmcp import FastMCP, Context, Image
from mcp.server.base import UserMessage, AssistantMessage

# Initialize the MCP server
mcp = FastMCP("EchidnaMCP")

# Utility functions
def run_command(cmd: List[str], cwd: Optional[str] = None) -> Dict[str, str]:
    """Run a shell command and return stdout, stderr, and return code."""
    try:
        process = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        return {
            "stdout": process.stdout,
            "stderr": process.stderr,
            "returncode": process.returncode,
        }
    except Exception as e:
        return {
            "stdout": "",
            "stderr": str(e),
            "returncode": -1,
        }

# Resources
@mcp.resource("resource://echidna-features")
def echidna_features() -> str:
    """Provide documentation on Echidna features."""
    features_path = Path(__file__).parent / "LLM" / "echdina-features.md"
    with open(features_path, "r") as f:
        return f.read()

# Tools
@mcp.tool()
async def run_echidna_test(
    contract_file: str,
    contract_name: Optional[str] = None,
    config_file: Optional[str] = None,
    test_mode: Optional[str] = None,
    test_limit: Optional[int] = None,
    seq_len: Optional[int] = None,
    corpus_dir: Optional[str] = None,
    ctx: Context = None,
) -> Dict[str, Any]:
    """
    Run Echidna on the specified Solidity contract.
    
    Args:
        contract_file: Path to the Solidity contract file
        contract_name: Optional contract name to test
        config_file: Optional path to Echidna config file
        test_mode: Optional test mode (property, assertion, optimization, etc.)
        test_limit: Optional test limit
        seq_len: Optional sequence length
        corpus_dir: Optional corpus directory
    
    Returns:
        The results of the Echidna test run
    """
    if ctx:
        await ctx.report_progress("Preparing Echidna test...", 1, 3)
    
    cmd = ["echidna", contract_file]
    
    if contract_name:
        cmd.extend(["--contract", contract_name])
    
    if config_file:
        cmd.extend(["--config", config_file])
    
    if test_mode:
        cmd.extend(["--test-mode", test_mode])
    
    if test_limit:
        cmd.extend(["--test-limit", str(test_limit)])
    
    if seq_len:
        cmd.extend(["--seq-len", str(seq_len)])
    
    if corpus_dir:
        cmd.extend(["--corpus-dir", corpus_dir])
    
    if ctx:
        await ctx.report_progress("Running Echidna...", 2, 3)
        await ctx.info(f"Running command: {' '.join(cmd)}")
    
    result = run_command(cmd)
    
    if ctx:
        await ctx.report_progress("Echidna test completed", 3, 3)
    
    return result

@mcp.tool()
async def create_echidna_config(
    config_params: Dict[str, Any],
    output_file: str,
    ctx: Context = None,
) -> Dict[str, Any]:
    """
    Create an Echidna configuration file with the provided parameters.
    
    Args:
        config_params: Dictionary of configuration parameters
        output_file: Path where to save the configuration file
    
    Returns:
        Status of the operation
    """
    if ctx:
        await ctx.report_progress("Creating Echidna config file...", 1, 2)
    
    try:
        with open(output_file, 'w') as f:
            for key, value in config_params.items():
                if isinstance(value, bool):
                    f.write(f"{key}: {str(value).lower()}\n")
                elif isinstance(value, (int, float)):
                    f.write(f"{key}: {value}\n")
                elif isinstance(value, str):
                    f.write(f"{key}: {value}\n")
                elif isinstance(value, list):
                    f.write(f"{key}: {json.dumps(value)}\n")
        
        if ctx:
            await ctx.report_progress("Config file created", 2, 2)
        
        return {
            "success": True,
            "message": f"Config file created at {output_file}",
            "file_path": output_file
        }
    
    except Exception as e:
        return {
            "success": False,
            "message": f"Error creating config file: {str(e)}"
        }

@mcp.tool()
async def create_solidity_contract(
    contract_code: str,
    output_file: str,
    ctx: Context = None,
) -> Dict[str, Any]:
    """
    Create a Solidity contract file with the provided code.
    
    Args:
        contract_code: The Solidity contract code
        output_file: Path where to save the contract file
    
    Returns:
        Status of the operation
    """
    if ctx:
        await ctx.report_progress("Creating Solidity contract file...", 1, 2)
    
    try:
        with open(output_file, 'w') as f:
            f.write(contract_code)
        
        if ctx:
            await ctx.report_progress("Contract file created", 2, 2)
        
        return {
            "success": True,
            "message": f"Contract file created at {output_file}",
            "file_path": output_file
        }
    
    except Exception as e:
        return {
            "success": False,
            "message": f"Error creating contract file: {str(e)}"
        }

@mcp.tool()
async def analyze_corpus(
    corpus_dir: str,
    ctx: Context = None,
) -> Dict[str, Any]:
    """
    Analyze an Echidna corpus directory to extract useful information.
    
    Args:
        corpus_dir: Path to the corpus directory
    
    Returns:
        Analysis of the corpus
    """
    if ctx:
        await ctx.report_progress("Analyzing corpus directory...", 1, 3)
    
    try:
        corpus_path = Path(corpus_dir)
        
        if not corpus_path.exists():
            return {
                "success": False,
                "message": f"Corpus directory {corpus_dir} does not exist"
            }
        
        # Look for coverage files
        coverage_files = list(corpus_path.glob("**/covered.*.txt"))
        
        # Look for test cases
        test_cases = list(corpus_path.glob("**/coverage/*.txt"))
        
        # Look for reproducers
        reproducers = list(corpus_path.glob("**/reproducers/*.txt"))
        
        if ctx:
            await ctx.report_progress("Reading corpus files...", 2, 3)
        
        # Process coverage files (extract sample info from first file)
        coverage_info = {}
        if coverage_files:
            with open(coverage_files[0], "r") as f:
                coverage_data = f.read()
                coverage_info = {
                    "sample": coverage_data[:500] + ("..." if len(coverage_data) > 500 else ""),
                    "size": len(coverage_data)
                }
        
        if ctx:
            await ctx.report_progress("Corpus analysis complete", 3, 3)
        
        return {
            "success": True,
            "corpus_dir": corpus_dir,
            "coverage_files": [str(f.relative_to(corpus_path)) for f in coverage_files],
            "test_cases": [str(f.relative_to(corpus_path)) for f in test_cases],
            "reproducers": [str(f.relative_to(corpus_path)) for f in reproducers],
            "coverage_sample": coverage_info
        }
    
    except Exception as e:
        return {
            "success": False,
            "message": f"Error analyzing corpus: {str(e)}"
        }

@mcp.tool()
async def filter_functions(
    contract_file: str,
    filter_list: List[str],
    blacklist: bool = True,
    output_config_file: str = "filter_config.yaml",
    ctx: Context = None,
) -> Dict[str, Any]:
    """
    Create an Echidna configuration file to filter specific functions.
    
    Args:
        contract_file: Path to the Solidity contract file
        filter_list: List of function signatures to filter
        blacklist: Whether to blacklist (True) or whitelist (False) functions
        output_config_file: Path where to save the configuration file
    
    Returns:
        Status of the operation
    """
    if ctx:
        await ctx.report_progress("Creating function filter config...", 1, 2)
    
    try:
        config = {
            "filterBlacklist": blacklist,
            "filterFunctions": filter_list
        }
        
        with open(output_config_file, 'w') as f:
            f.write(f"filterBlacklist: {str(blacklist).lower()}\n")
            f.write(f"filterFunctions: {json.dumps(filter_list)}\n")
        
        if ctx:
            await ctx.report_progress("Filter config created", 2, 2)
        
        return {
            "success": True,
            "message": f"Filter configuration created at {output_config_file}",
            "file_path": output_config_file,
            "config": config
        }
    
    except Exception as e:
        return {
            "success": False,
            "message": f"Error creating filter config: {str(e)}"
        }

@mcp.tool()
async def setup_end_to_end_test(
    contract_file: str,
    test_file: str = None,
    ctx: Context = None,
) -> Dict[str, Any]:
    """
    Set up an end-to-end test with Etheno and Echidna.
    
    Args:
        contract_file: Path to the Solidity contract file
        test_file: Optional path to the test file
    
    Returns:
        Result of the setup operation
    """
    if ctx:
        await ctx.report_progress("Setting up Etheno for end-to-end testing...", 1, 4)
    
    # Start Etheno
    etheno_cmd = ["etheno", "--ganache", "--ganache-args=--miner.blockGasLimit 10000000", "-x", "init.json"]
    etheno_result = run_command(etheno_cmd)
    
    if etheno_result["returncode"] != 0:
        return {
            "success": False,
            "message": "Failed to start Etheno",
            "etheno_output": etheno_result
        }
    
    if ctx:
        await ctx.report_progress("Running test on Ganache...", 2, 4)
    
    # Run the test on Ganache
    test_cmd = ["truffle", "test"]
    if test_file:
        test_cmd.append(test_file)
    test_cmd.extend(["--network", "develop"])
    
    test_result = run_command(test_cmd)
    
    if ctx:
        await ctx.report_progress("Creating Echidna config...", 3, 4)
    
    # Create Echidna config
    config = {
        "prefix": "crytic_",
        "initialize": "init.json",
        "allContracts": True
    }
    
    with open("echidna.yaml", 'w') as f:
        for key, value in config.items():
            if isinstance(value, bool):
                f.write(f"{key}: {str(value).lower()}\n")
            else:
                f.write(f"{key}: {value}\n")
    
    if ctx:
        await ctx.report_progress("End-to-end setup completed", 4, 4)
    
    return {
        "success": True,
        "message": "End-to-end testing setup completed",
        "etheno_output": etheno_result,
        "test_output": test_result,
        "echidna_config": "echidna.yaml",
        "next_steps": [
            "Review init.json to find deployed contract addresses",
            "Create an E2E.sol file with properties to test",
            "Run Echidna with: echidna . --contract E2E --config echidna.yaml"
        ]
    }

@mcp.tool()
async def generate_property_template(
    contract_name: str,
    property_type: str = "boolean",
    ctx: Context = None,
) -> Dict[str, Any]:
    """
    Generate a template for an Echidna property based on the specified type.
    
    Args:
        contract_name: Name of the contract being tested
        property_type: Type of property (boolean, assertion, dapptest)
    
    Returns:
        Template code for the property
    """
    if ctx:
        await ctx.report_progress("Generating property template...", 1, 2)
    
    templates = {
        "boolean": f"""contract Test{contract_name} is {contract_name} {{
    function echidna_property_description() public returns (bool) {{
        // Property logic here
        return true; // Property holds
    }}
}}""",
        
        "assertion": f"""contract Test{contract_name} is {contract_name} {{
    function check_invariant() public {{
        // Test logic here
        assert(true); // Property holds
    }}
}}""",
        
        "dapptest": f"""contract Test{contract_name} is {contract_name} {{
    function testProperty(uint256 param1) public {{
        // Test logic with parameters
        // Will fail if it reverts (except with "FOUNDRY::ASSUME" reason)
    }}
}}""",
        
        "optimization": f"""contract Test{contract_name} is {contract_name} {{
    function echidna_opt_function() public view returns (int256) {{
        // Return a value to maximize
        return 0;
    }}
}}"""
    }
    
    if property_type not in templates:
        return {
            "success": False,
            "message": f"Unknown property type: {property_type}. Available types: {', '.join(templates.keys())}"
        }
    
    if ctx:
        await ctx.report_progress("Template generated", 2, 2)
    
    return {
        "success": True,
        "template": templates[property_type],
        "property_type": property_type,
        "usage_notes": get_property_usage_notes(property_type)
    }

def get_property_usage_notes(property_type: str) -> str:
    """Return usage notes for a specific property type."""
    notes = {
        "boolean": """
- Function name must start with 'echidna_'
- Must return a boolean (true if property holds)
- Side effects are reverted after execution
- Will fail if it returns false or reverts
        """,
        
        "assertion": """
- Use assert() to check conditions
- Will fail if assert fails
- Can also emit AssertionFailed event to indicate failure
- Side effects are preserved
        """,
        
        "dapptest": """
- Requires one or more arguments
- Will fail if execution reverts
- Can use "FOUNDRY::ASSUME" revert reason to skip invalid inputs
- Typically used with stateless testing (--seq-len 1)
        """,
        
        "optimization": """
- Function name must start with 'echidna_opt_'
- Must return an int256 value
- Echidna will try to maximize this value
- Run with --test-mode optimization
        """
    }
    return notes.get(property_type, "")

@mcp.tool()
async def create_assertion_contract(
    contract_to_test: str,
    properties: List[Dict[str, str]],
    output_file: str,
    ctx: Context = None,
) -> Dict[str, Any]:
    """
    Create a Solidity contract with assertion-based properties.
    
    Args:
        contract_to_test: Name of the contract to test
        properties: List of property dictionaries, each with 'name' and 'condition'
        output_file: Path to save the contract file
    
    Returns:
        Result of the operation
    """
    if ctx:
        await ctx.report_progress("Creating assertion contract...", 1, 2)
    
    try:
        contract_code = f"""// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "./{contract_to_test}.sol";

contract Test{contract_to_test} is {contract_to_test} {{
    // Define event that Echidna will detect
    event AssertionFailed(string message);
    
"""
        
        for prop in properties:
            contract_code += f"""    function {prop['name']}() public {{
        if (!({prop['condition']})) {{
            emit AssertionFailed("{prop['name']} failed");
        }}
    }}
    
"""
        
        contract_code += "}"
        
        with open(output_file, 'w') as f:
            f.write(contract_code)
        
        if ctx:
            await ctx.report_progress("Assertion contract created", 2, 2)
        
        return {
            "success": True,
            "message": f"Assertion contract created at {output_file}",
            "file_path": output_file,
            "contract_code": contract_code
        }
    
    except Exception as e:
        return {
            "success": False,
            "message": f"Error creating assertion contract: {str(e)}"
        }

@mcp.tool()
async def create_fork_test(
    contract_code: str, 
    output_file: str,
    rpc_url: str,
    block_number: Optional[int] = None,
    ctx: Context = None,
) -> Dict[str, Any]:
    """
    Create a Solidity contract for testing with state forking from an RPC provider.
    
    Args:
        contract_code: The Solidity contract code to use for testing
        output_file: Path to save the contract file
        rpc_url: The RPC URL to fork from
        block_number: Optional block number to fork from
    
    Returns:
        Result of the operation and next steps
    """
    if ctx:
        await ctx.report_progress("Creating state fork test...", 1, 3)
    
    try:
        with open(output_file, 'w') as f:
            f.write(contract_code)
        
        # Create a shell script to run the test with the RPC environment variables
        script_path = Path(output_file).with_suffix('.sh')
        with open(script_path, 'w') as f:
            f.write("#!/bin/bash\n\n")
            f.write(f"export ECHIDNA_RPC_URL={rpc_url}\n")
            if block_number:
                f.write(f"export ECHIDNA_RPC_BLOCK={block_number}\n")
            f.write("\n")
            f.write(f"echidna {output_file} --test-mode assertion\n")
        
        # Make the script executable
        os.chmod(script_path, 0o755)
        
        if ctx:
            await ctx.report_progress("Fork test created", 3, 3)
        
        return {
            "success": True,
            "message": f"Fork test created at {output_file}",
            "contract_file": output_file,
            "script_file": str(script_path),
            "next_steps": [
                f"Run the test with: sh {script_path}",
                "Or manually set environment variables:",
                f"ECHIDNA_RPC_URL={rpc_url} " + 
                (f"ECHIDNA_RPC_BLOCK={block_number} " if block_number else "") + 
                f"echidna {output_file} --test-mode assertion"
            ]
        }
    
    except Exception as e:
        return {
            "success": False,
            "message": f"Error creating fork test: {str(e)}"
        }

@mcp.tool()
async def visualize_coverage(
    corpus_dir: str,
    output_format: str = "text",
    ctx: Context = None,
) -> Union[Dict[str, Any], Image]:
    """
    Visualize code coverage from an Echidna corpus.
    
    Args:
        corpus_dir: Path to the corpus directory
        output_format: Format for visualization (text or image)
    
    Returns:
        Coverage visualization
    """
    if ctx:
        await ctx.report_progress("Analyzing coverage data...", 1, 3)
    
    try:
        corpus_path = Path(corpus_dir)
        
        if not corpus_path.exists():
            return {
                "success": False,
                "message": f"Corpus directory {corpus_dir} does not exist"
            }
        
        # Find coverage files
        coverage_files = list(corpus_path.glob("**/covered.*.txt"))
        
        if not coverage_files:
            return {
                "success": False,
                "message": "No coverage files found in corpus directory"
            }
        
        # Parse the most recent coverage file
        coverage_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        most_recent = coverage_files[0]
        
        with open(most_recent, "r") as f:
            coverage_data = f.readlines()
        
        # Process coverage data
        if ctx:
            await ctx.report_progress("Processing coverage data...", 2, 3)
        
        if output_format == "text":
            if ctx:
                await ctx.report_progress("Coverage visualization complete", 3, 3)
            
            return {
                "success": True,
                "format": "text",
                "coverage_file": str(most_recent),
                "coverage_data": "".join(coverage_data[:100]) + "..." if len(coverage_data) > 100 else "".join(coverage_data),
                "total_lines": len(coverage_data),
                "covered_lines": sum(1 for line in coverage_data if '*' in line)
            }
        
        elif output_format == "image":
            # This is a placeholder for actual image generation
            # In a real implementation, you would generate a coverage visualization image
            if ctx:
                await ctx.report_progress("Image generation not implemented", 3, 3)
            
            return {
                "success": False,
                "message": "Image visualization not implemented yet. Use text format instead."
            }
        
        else:
            return {
                "success": False,
                "message": f"Unknown output format: {output_format}. Supported formats: text, image"
            }
    
    except Exception as e:
        return {
            "success": False,
            "message": f"Error visualizing coverage: {str(e)}"
        }

@mcp.prompt()
def echidna_help() -> List[Union[UserMessage, AssistantMessage]]:
    """Provide help information about using Echidna with MCP."""
    return [
        UserMessage("How do I use Echidna with this MCP server?"),
        AssistantMessage("""
# Echidna MCP Server

This MCP server provides tools for smart contract analysis using the Echidna fuzzer.

## Available Tools

1. `run_echidna_test` - Run Echidna on a Solidity contract file
2. `create_echidna_config` - Create an Echidna configuration file
3. `create_solidity_contract` - Create a Solidity file with provided code
4. `analyze_corpus` - Analyze an Echidna corpus directory
5. `filter_functions` - Create a config to filter functions for testing
6. `setup_end_to_end_test` - Set up end-to-end testing with Etheno
7. `generate_property_template` - Generate template code for various property types
8. `create_assertion_contract` - Create a contract with assertion-based properties
9. `create_fork_test` - Create a test using state forking from an RPC provider
10. `visualize_coverage` - Visualize code coverage data from an Echidna corpus

## Common Usage Patterns

### Testing a Smart Contract

1. Create your Solidity contract with Echidna properties
2. Run Echidna test using the `run_echidna_test` tool
3. Analyze the results

### Using Corpus Data

1. Set up a corpus directory in your Echidna config
2. Run tests to collect corpus data
3. Analyze the corpus using `analyze_corpus`

### End-to-End Testing

1. Use `setup_end_to_end_test` to capture transactions
2. Create an E2E.sol file with properties to test
3. Run Echidna with the generated config

### Testing with State Forking

1. Create a test contract using `create_fork_test`
2. Run the test with RPC environment variables set
3. Analyze results to identify issues on the live network
""")
    ]

def main():
    """Start the MCP server using stdio transport."""
    mcp.run()


if __name__ == "__main__":
    main()
