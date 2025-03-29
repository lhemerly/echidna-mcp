Introduction to Property-Based Fuzzing
Echidna is a property-based fuzzer, which we have described in our previous blog posts (1, 2, 3).

Fuzzing
Fuzzing is a well-known technique in the security community. It involves generating more or less random inputs to find bugs in a program. Fuzzers for traditional software (such as AFL or LibFuzzer) are known to be efficient tools for bug discovery.

Beyond purely random input generation, there are many techniques and strategies used for generating good inputs, including:

Obtaining feedback from each execution and guiding input generation with it. For example, if a newly generated input leads to the discovery of a new path, it makes sense to generate new inputs closer to it.
Generating input with respect to a structural constraint. For instance, if your input contains a header with a checksum, it makes sense to let the fuzzer generate input that validates the checksum.
Using known inputs to generate new inputs. If you have access to a large dataset of valid input, your fuzzer can generate new inputs from them, rather than starting from scratch for each generation. These are usually called seeds.
Property-Based Fuzzing
Echidna belongs to a specific family of fuzzers: property-based fuzzing, which is heavily inspired by QuickCheck. In contrast to a classic fuzzer that tries to find crashes, Echidna aims to break user-defined invariants.

In smart contracts, invariants are Solidity functions that can represent any incorrect or invalid state that the contract can reach, including:

Incorrect access control: The attacker becomes the owner of the contract.
Incorrect state machine: Tokens can be transferred while the contract is paused.
Incorrect arithmetic: The user can underflow their balance and get unlimited free tokens.

Testing a Property with Echidna
Table of Contents:

Testing a Property with Echidna
Introduction
Write a Property
Initiate a Contract
Run Echidna
Summary: Testing a Property
Introduction
This tutorial demonstrates how to test a smart contract with Echidna. The target is the following smart contract (token.sol):

contract Token {
    mapping(address => uint256) public balances;

    function airdrop() public {
        balances[msg.sender] = 1000;
    }

    function consume() public {
        require(balances[msg.sender] > 0);
        balances[msg.sender] -= 1;
    }

    function backdoor() public {
        balances[msg.sender] += 1;
    }
}
We will assume that this token has the following properties:

Anyone can hold a maximum of 1000 tokens.

The token cannot be transferred (it is not an ERC20 token).

Write a Property
Echidna properties are Solidity functions. A property must:

Have no arguments.

Return true if successful.

Have its name starting with echidna.

Echidna will:

Automatically generate arbitrary transactions to test the property.

Report any transactions that lead a property to return false or throw an error.

Discard side-effects when calling a property (i.e., if the property changes a state variable, it is discarded after the test).

The following property checks that the caller can have no more than 1000 tokens:

function echidna_balance_under_1000() public view returns (bool) {
    return balances[msg.sender] <= 1000;
}
Use inheritance to separate your contract from your properties:

contract TestToken is Token {
    function echidna_balance_under_1000() public view returns (bool) {
        return balances[msg.sender] <= 1000;
    }
}
testtoken.sol implements the property and inherits from the token.

Initiate a Contract
Echidna requires a constructor without input arguments. If your contract needs specific initialization, you should do it in the constructor.

There are some specific addresses in Echidna:

0x30000 calls the constructor.

0x10000, 0x20000, and 0x30000 randomly call other functions.

We don't need any particular initialization in our current example. As a result, our constructor is empty.

Run Echidna
Launch Echidna with:

echidna contract.sol
If contract.sol contains multiple contracts, you can specify the target:

echidna contract.sol --contract MyContract
Summary: Testing a Property
The following summarizes the Echidna run on our example:

contract TestToken is Token {
    constructor() public {}

    function echidna_balance_under_1000() public view returns (bool) {
        return balances[msg.sender] <= 1000;
    }
}
echidna testtoken.sol --contract TestToken
...

echidna_balance_under_1000: failed!💥
  Call sequence, shrinking (1205/5000):
    airdrop()
    backdoor()

...
Echidna found that the property is violated if the backdoor function is called.

How to Select the Most Suitable Testing Mode
Echidna offers several ways to write properties, which often leaves developers and auditors wondering about the most appropriate testing mode to use. In this section, we will review how each mode works, as well as their advantages and disadvantages.

Table of Contents:

Introduction
Boolean Properties
Assertions
Dapptest
Other testing modes
Stateless vs. Stateful
Introduction
Echidna offer a variety of different testing modes. These can be selected using the testingMode config option or using the --testing-mode parameter. Each mode will be explained, highlighting the keyword needed for the configuration.

Boolean Properties
By default, the property testing mode is used, which reports failures using special functions called properties:

Testing functions should be named with a specific prefix (e.g. echidna_).
Testing functions take no parameters and always return a boolean value.
Any side effect will be reverted at the end of the execution of the property.
Properties pass if they return true and fail if they return false or revert. Alternatively, properties that start with "echidnarevert" will fail if they return any value (true or false) and pass if they revert. This pseudo-code summarizes how properties work:
function echidna_property() public returns (bool) { // No arguments are required
  // The following statements can trigger a failure if they revert
  publicFunction(...);
  internalFunction(...);
  contract.function(...);

  // The following statement can trigger a failure depending on the returned value
  return ...;
} // side effects are *not* preserved

function echidna_revert_property() public returns (bool) { // No arguments are required
  // The following statements can *never* trigger a failure
  publicFunction(...);
  internalFunction(...);
  contract.function(...);

  // The following statement will *always* trigger a failure regardless of the value returned
  return ...;
} // side effects are *not* preserved
Advantages:
Properties can be easier to write and understand compared to other approaches for testing.
No need to worry about side effects since these are reverted at the end of the property execution.
Disadvantages:
Since the properties take no parameters, any additional input should be added using a state variable.
Any revert will be interpreted as a failure, which is not always expected.
No coverage is collected during its execution so these properties should be used with simple code. For anything complex (e.g., with a non-trivial amount of branches), other types of tests should be used.
Recommendations
This mode can be used when a property can be easily computed from the use of state variables (either internal or public), and there is no need to use extra parameters.

Assertions
Using the assertion testing mode, Echidna will report an assert violation if:

The execution reverts during a call to assert. Technically speaking, Echidna will detect an assertion failure if it executes an assert call that fails in the first call frame of the target contract (so this excludes most internal transactions).
An AssertionFailed event (with any number of parameters) is emitted by any contract. This pseudo-code summarizes how assertions work:
function checkInvariant(...) public { // Any number of arguments is supported
  // The following statements can trigger a failure using `assert`
  assert(...);
  publicFunction(...);
  internalFunction(...);

  // The following statement will always trigger a failure even if the execution ends with a revert
  emits AssertionFailed(...);

  // The following statement will *only* trigger a failure using `assert` if using solc 0.8.x or newer
  // To make sure it works in older versions, use the AssertionFailed(...) event
  anotherContract.function(...);

} // side effects are preserved
Functions checking assertions do not require any particular name and are executed like any other function; therefore, their side effects are retained if they do not revert.

Advantages
Easy to implement, especially if several parameters are required to compute the invariant.
Coverage is collected during the execution of these tests, so it can help to discover new failures.
If the code base already contains assertions for checking invariants, they can be reused.
Disadvantages
If the code to test is already using assertions for data validation, it will not work as expected. For example:
function deposit(uint256 tokens) public {
  assert(tokens > 0); // should be strictly positive
  ...
}
Developers should avoid doing that and use require instead, but if that is not possible because you are calling some contract that is outside your control, you can use the AssertionFailure event.

Recommendation
You should use assertions if your invariant is more naturally expressed using arguments or can only be checked in the middle of a transaction. Another good use case of assertions is complex code that requires checking something as well as changing the state. In the following example, we test staking some ERC20, given that there are at least MINSTAKE tokens in the sender balance.

function testStake(uint256 toStake) public {
    uint256 balance = balanceOf(msg.sender);
    toStake = toStake % (balance + 1);
    if (toStake < MINSTAKE) return; // Pre: minimal stake is required
    stake(msg.sender, toStake); // Action: token staking
    assert(staked(msg.sender) == toStake); // Post: staking amount is toStake
    assert(balanceOf(msg.sender) == balance - toStake); // Post: balance decreased
}
testStake checks some invariants on staking and also ensures that the contract's state is updated properly (e.g., allowing a user to stake at least MINSTAKE).

Dapptest
Using the dapptest testing mode, Echidna will report violations using certain functions following how dapptool and foundry work:

This mode uses any function name with one or more arguments, which will trigger a failure if they revert, except in one special case. Specifically, if the execution reverts with the special reason “FOUNDRY::ASSUME”, then the test will pass (this emulates how the assume foundry cheat code works). This pseudo-code summarizes how dapptests work:
function checkDappTest(..) public { // One or more arguments are required
  // The following statements can trigger a failure if they revert
  publicFunction(..);
  internalFunction(..);
  anotherContract.function(..);

  // The following statement will never trigger a failure
  require(.., “FOUNDRY::ASSUME”);
}
Functions implementing these tests do not require any particular name and are executed like any other function; therefore, their side effects are retained if they do not revert (typically, this mode is used only in stateless testing).
The function should NOT be payable (but this can change in the future)
Advantages:
Easy to implement, particularly for stateless mode.
Coverage is collected during the execution of these tests, so it can help to discover new failures.
Disadvantages:
Almost any revert will be interpreted as a failure, which is not always expected. To avoid this, you should use reverts with FOUNDRY::ASSUME or use try/catch.
Recommendation
Use dapptest mode if you are testing stateless invariants and the code will never unexpectedly revert. Avoid using it for stateful testing, as it was not designed for that (although Echidna supports it).

Other testing modes
Echidna allows other testing mode, which are less frecuently used:

overflow mode: this mode is similar to assertion but it will only catch integer overflow (so no need to define any function with assertions). It only works in solc 0.8.x or greater, for code outside unchecked blocks.
optimization mode: this mode allows to maximize the value returned by a function. It is explained in detail in its own tutorial.
exploration mode: this mode will not use any kind of invariants to check, allowing Echidna to collect coverage.
Stateless vs. Stateful
Any of these testing modes can be used, in either stateful (by default) or stateless mode (using --seqLen 1). In stateful mode, Echidna will maintain the state between each function call and attempt to break the invariants. In stateless mode, Echidna will discard state changes during fuzzing. There are notable differences between these two modes.

Stateful is more powerful and can allow breaking invariants that exist only if the contract reaches a specific state.
Stateless tests benefit from simpler input generation and are generally easier to use than stateful tests.
Stateless tests can hide issues since some of them depend on a sequence of operations that is not reachable in a single transaction.
Stateless mode forces resetting the EVM after each transaction or test, which is usually slower than resetting the state once every certain amount of transactions (by default, every 100 transactions).
Recommendations
For beginners, we recommend starting with Echidna in stateless mode and switching to stateful once you have a good understanding of the system's invariants.

Common Testing Approaches
Testing smart contracts is not as straightforward as testing normal binaries that you run on your local computer. This is due to the existence of multiple accounts interacting with one or many entry points. While a fuzzer can simulate the Ethereum Virtual Machine and can potentially use any account with any feature (e.g., an unlimited amount of ETH), we take care not to break some essential underlying assumptions of transactions that are impossible in Ethereum (e.g., using msg.sender as the zero address). That is why it is crucial to have a clear view of the system to test and how transactions will be simulated. We can classify the testing approach into several categories. We will start with two of them: internal and external.

Table of contents:

Common Testing Approaches
Internal Testing
External Testing
Partial Testing
Internal Testing
In this testing approach, properties are defined within the contract to test, giving complete access to the internal state of the system.

contract InternalTest is System {
    function echidna_state_greater_than_X() public returns (bool) {
        return stateVar > X;
    }
}
With this approach, Echidna generates transactions from a simulated account to the target contract. This testing approach is particularly useful for simpler contracts that do not require complex initialization and have a single entry point. Additionally, properties can be easier to write, as they can access the system's internal state.

External Testing
In the external testing approach, properties are tested using external calls from a different contract. Properties are only allowed to access external/public variables or functions.

contract ExternalTest {
    constructor() public {
        addr = address(0x1234);
    }

    function echidna_state_greater_than_X() public returns (bool) {
        return System(addr).stateVar() > X;
    }
}
This testing approach is useful for dealing with contracts requiring external initialization (e.g., using Etheno). However, the method of how Echidna runs the transactions should be handled correctly, as the contract with the properties is no longer the one we want to test. Since ExternalTest defines no additional methods, running Echidna directly on this will not allow any code execution from the contract to test (no functions in ExternalTest to call besides the actual properties). In this case, there are several alternatives:

Contract wrapper: Define specific operations to "wrap" the system for testing. For each operation that we want Echidna to execute in the system to test, we add one or more functions that perform an external call to it.

contract ExternalTest {
    constructor() public {
       // addr = ...;
    }

    function method(...) public returns (...) {
        return System(addr).method();
    }

    function echidna_state_greater_than_X() public returns (bool) {
        return System(addr).stateVar() > X;
    }
}
There are two important points to consider with this approach:

The sender of each transaction will be the ExternalTest contract, instead of the simulated Echidna senders (e.g., 0x10000, ..). This means that the real address interacting with the system will be the External contract's address, rather than one of the Echidna senders. Please take special care if this contract needs to be provided ETH or tokens.

This approach is manual and can be time-consuming if there are many function operations. However, it can be useful when Echidna needs help calculating a value that cannot be randomly sampled:

contract ExternalTest {
    // ...

    function methodUsingF(..., uint256 x) public returns (...) {
       return System(addr).method(.., f(x));
    }

    ...
}
allContracts: Echidna can perform direct calls to every contract if the allContracts mode is enabled. This means that using it does not require wrapped calls. However, since every deployed contract can be called, unintended effects may occur. For example, if we have a property to ensure that the amount of tokens is limited:

contract ExternalTest {
    constructor() {
       addr = ...;
       MockERC20(...).mint(...);
    }

    function echidna_limited_supply() public returns (bool) {
       return System(addr).balanceOf(...) <= X;
    }

    ...
}
Using "mock" contracts for tokens (e.g., MockERC20) could be an issue because Echidna could call functions that are public but are only supposed to be used during the initialization, such as mint. This can be easily solved using a blacklist of functions to ignore:

filterBlacklist: true
filterFunctions: [“MockERC20.mint(uint256, address)”]
Another benefit of using this approach is that it forces the developer or auditor to write properties using public data. If an essential property cannot be defined using public data, it could indicate that users or other contracts will not be able to easily interact with the system to perform an operation or verify that the system is in a valid state.

Partial Testing
Ideally, testing a smart contract system uses the complete deployed system, with the same parameters that the developers intend to use. Testing with the real code is always preferred, even if it is slower than other methods (except for cases where it is extremely slow). However, there are many cases where, despite the complete system being deployed, it cannot be simulated because it depends on off-chain components (e.g., a token bridge). In these cases, alternative solutions must be implemented.

With partial testing, we test some of the components, ignoring or abstracting uninteresting parts such as standard ERC20 tokens or oracles. There are several ways to do this.

Isolated testing: If a component is adequately abstracted from the rest of the system, testing it can be easy. This method is particularly useful for testing stateless properties found in components that compute mathematical operations, such as mathematical libraries.

Function override: Solidity allows for function overriding, used to change the functionality of a code segment without affecting the rest of the codebase. We can use this to disable certain functions in our tests to allow testing with Echidna:

contract InternalTestOverridingSignatures is System {
    function verifySignature(...) public override returns (bool) {
        return true; // signatures are always valid
    }

    function echidna_state_greater_than_X() public returns (bool) {
        executeSomethingWithSignature(...);
        return stateVar > X;
    }
}
Model testing: If the system is not modular enough, a different approach is required. Instead of using the code as is, we will create a "model" of the system in Solidity, using mostly the original code. Although there is no defined list of steps to build a model, we can provide a generic example. Suppose we have a complex system that includes this piece of code:

contract System {
    ...

    function calculateSomething() public returns (uint256) {
        if (booleanState) {
            stateSomething = (uint256State1 * uint256State2) / 2 ** 128;
            return stateSomething / uint128State;
        }

        ...
    }
}
Where boolState, uint256State1, uint256State2, and stateSomething are state variables of our system to test. We will create a model (e.g., copy, paste, and modify the original code in a new contract), where each state variable is transformed into a parameter:

contract SystemModel {
    function calculateSomething(bool boolState, uint256 uint256State1, ...) public returns (uint256) {
        if (boolState) {
            stateSomething = (uint256State1 * uint256State2) / 2 ** 128;
            return stateSomething / uint128State;
        }
        ...
    }
}
At this point, we should be able to compile our model without any dependency on the original codebase (everything necessary should be included in the model). We can then insert assertions to detect when the returned value exceeds a certain threshold.

While developers or auditors may be tempted to quickly create tests using this technique, there are certain disadvantages when creating models:

The tested code can be very different from what we want to test. This can either introduce unreal issues (false positives) or hide real issues from the original code (false negatives). In the example, it is unclear if the state variables can take arbitrary values.

The model will have limited value if the code changes since any modification to the original model will require manually rebuilding the model.

In any case, developers should be warned that their code is difficult to test and should refactor it to avoid this issue in the future.

Filtering Functions for Fuzzing Campaigns
Table of contents:

Filtering Functions for Fuzzing Campaigns
Introduction
Filtering functions
Running Echidna
Summary: Filtering functions
Introduction
In this tutorial, we'll demonstrate how to filter specific functions to be fuzzed using Echidna. We'll use the following smart contract multi.sol as our target:

contract C {
    bool state1 = false;
    bool state2 = false;
    bool state3 = false;
    bool state4 = false;

    function f(uint256 x) public {
        require(x == 12);
        state1 = true;
    }

    function g(uint256 x) public {
        require(state1);
        require(x == 8);
        state2 = true;
    }

    function h(uint256 x) public {
        require(state2);
        require(x == 42);
        state3 = true;
    }

    function i() public {
        require(state3);
        state4 = true;
    }

    function reset1() public {
        state1 = false;
        state2 = false;
        state3 = false;
        return;
    }

    function reset2() public {
        state1 = false;
        state2 = false;
        state3 = false;
        return;
    }

    function echidna_state4() public returns (bool) {
        return (!state4);
    }
}
The small contract above requires Echidna to find a specific sequence of transactions to modify a certain state variable, which is difficult for a fuzzer. It's recommended to use a symbolic execution tool like Manticore in such cases. Let's run Echidna to verify this:

echidna multi.sol
...
echidna_state4: passed! 🎉
Seed: -3684648582249875403
Filtering Functions
Echidna has difficulty finding the correct sequence to test this contract because the two reset functions (reset1 and reset2) revert all state variables to false. However, we can use a special Echidna feature to either blacklist the reset functions or whitelist only the f, g, h, and i functions.

To blacklist functions, we can use the following configuration file:

filterBlacklist: true
filterFunctions: ["C.reset1()", "C.reset2()"]
Alternatively, we can whitelist specific functions by listing them in the configuration file:

filterBlacklist: false
filterFunctions: ["C.f(uint256)", "C.g(uint256)", "C.h(uint256)", "C.i()"]
filterBlacklist is true by default.
Filtering will be performed based on the full function name (contract name + "." + ABI function signature). If you have f() and f(uint256), you can specify exactly which function to filter.
Running Echidna
To run Echidna with a configuration file blacklist.yaml:

echidna multi.sol --config blacklist.yaml
...
echidna_state4: failed!💥
  Call sequence:
    f(12)
    g(8)
    h(42)
    i()
Echidna will quickly discover the sequence of transactions required to falsify the property.

Summary: Filtering Functions
Echidna can either blacklist or whitelist functions to call during a fuzzing campaign using:

filterBlacklist: true
filterFunctions: ["C.f1()", "C.f2()", "C.f3()"]
echidna contract.sol --config config.yaml
...
Depending on the value of the filterBlacklist boolean, Echidna will start a fuzzing campaign by either blacklisting C.f1(), C.f2(), and C.f3() or by only calling those functions.

How to Test Assertions with Echidna
Table of contents:

How to Test Assertions with Echidna
Introduction
Write an Assertion
Run Echidna
When and How to Use Assertions
Summary: Assertion Checking
Introduction
In this short tutorial, we will demonstrate how to use Echidna to check assertions in smart contracts.

Write an Assertion
Let's assume we have a contract like this one:

contract Incrementor {
    uint256 private counter = 2 ** 200;

    function inc(uint256 val) public returns (uint256) {
        uint256 tmp = counter;
        unchecked {
            counter += val;
        }
        // tmp <= counter
        return (counter - tmp);
    }
}
We want to ensure that tmp is less than or equal to counter after returning its difference. We could write an Echidna property, but we would need to store the tmp value somewhere. Instead, we can use an assertion like this one (assert.sol):

contract Incrementor {
    uint256 private counter = 2 ** 200;

    function inc(uint256 val) public returns (uint256) {
        uint256 tmp = counter;
        unchecked {
            counter += val;
        }
        assert(tmp <= counter);
        return (counter - tmp);
    }
}
We can also use a special event called AssertionFailed with any number of parameters to inform Echidna about a failed assertion without using assert. This will work in any contract. For example:

contract Incrementor {
    event AssertionFailed(uint256);

    uint256 private counter = 2 ** 200;

    function inc(uint256 val) public returns (uint256) {
        uint256 tmp = counter;
        unchecked {
            counter += val;
        }
        if (tmp > counter) {
            emit AssertionFailed(counter);
        }
        return (counter - tmp);
    }
}
Run Echidna
To enable assertion failure testing in Echidna, you can use --test-mode assertion directly from the command line.

Alternatively, you can create an Echidna configuration file, config.yaml, with testMode set for assertion checking:

testMode: assertion
When we run this contract with Echidna, we receive the expected results:

echidna assert.sol --test-mode assertion
Analyzing contract: assert.sol:Incrementor
assertion in inc: failed!💥
  Call sequence, shrinking (2596/5000):
    inc(21711016731996786641919559689128982722488122124807605757398297001483711807488)
    inc(7237005577332262213973186563042994240829374041602535252466099000494570602496)
    inc(86844066927987146567678238756515930889952488499230423029593188005934847229952)

Seed: 1806480648350826486
As you can see, Echidna reports an assertion failure in the inc function. It is possible to add multiple assertions per function; however, Echidna cannot determine which assertion failed.

When and How to Use Assertions
Assertions can be used as alternatives to explicit properties if the conditions to check are directly related to the correct use of some operation f. Adding assertions after some code will enforce that the check happens immediately after it is executed:

function f(bytes memory args) public {
    // some complex code
    // ...
    assert(condition);
    // ...
}
In contrast, using an explicit Boolean property will randomly execute transactions, and there is no easy way to enforce exactly when it will be checked. It is still possible to use this workaround:

function echidna_assert_after_f() public returns (bool) {
    f(args);
    return (condition);
}
However, there are some issues:

It does not compile if f is declared as internal or external
It is unclear which arguments should be used to call f
The property will fail if f reverts
Assertions can help overcome these potential issues. For instance, they can be easily detected when calling internal or public functions:

function f(bytes memory args) public {
    // some complex code
    // ...
    g(otherArgs) // this contains an assert
    // ...
}
If g is external, then assertion failure can be only detected in Solidity 0.8.x or later.

function f(bytes memory args) public {
    // some complex code
    // ...
    contract.g(otherArgs) // this contains an assert
    // ...
}
In general, we recommend following John Regehr's advice on using assertions:

Do not force any side effects during the assertion checking. For instance: assert(ChangeStateAndReturn() == 1)
Do not assert obvious statements. For instance assert(var >= 0) where var is declared as uint256.
Finally, please do not use require instead of assert, since Echidna will not be able to detect it (but the contract will revert anyway).

Summary: Assertion Checking
The following summarizes the run of Echidna on our example (remember to use 0.7.x or older):

contract Incrementor {
    uint256 private counter = 2 ** 200;

    function inc(uint256 val) public returns (uint256) {
        uint256 tmp = counter;
        counter += val;
        assert(tmp <= counter);
        return (counter - tmp);
    }
}
echidna assert.sol --test-mode assertion
Analyzing contract: assert.sol:Incrementor
assertion in inc: failed!💥
  Call sequence, shrinking (2596/5000):
    inc(21711016731996786641919559689128982722488122124807605757398297001483711807488)
    inc(7237005577332262213973186563042994240829374041602535252466099000494570602496)
    inc(86844066927987146567678238756515930889952488499230423029593188005934847229952)

Seed: 1806480648350826486
Echidna discovered that the assertion in inc can fail if this function is called multiple times with large arguments.

Using ether during a fuzzing campaign
Table of contents:

Using ether during a fuzzing campaign
Introduction
Controlling the amount of ether in payable functions
Controlling the amount of ether in contracts
Summary: Working with ether
Introduction
We will see how to use ether during a fuzzing campaign. The following smart contract will be used as example:

contract C {
    function pay() public payable {
        require(msg.value == 12000);
    }

    function echidna_has_some_value() public returns (bool) {
        return (address(this).balance != 12000);
    }
}
This code forces Echidna to send a particular amount of ether as value in the pay function. Echidna will do this for each payable function in the target function (or any contract if allContracts is enabled):

$ echidna balanceSender.sol
...
echidna_has_some_value: failed!💥
  Call sequence:
    pay() Value: 0x2ee0
Echidna will show the value amount in hexadecimal.

Controlling the amount of ether in payable functions
The amount of ether to send in each payable function will be randomly selected, but with a maximum value determined by the maxValue value with a default of 100 ether per transaction:

maxValue: 100000000000000000000
This means that each transaction will contain, at most, 100 ether in value. However, there is no maximum that will be used in total. The maximum amount to receive will be determined by the number of transactions. If you are using 100 transactions (--seq-len 100), then the total amount of ether used for all the transactions will be between 0 and 100 * 100 ethers.

Keep in mind that the balance of the senders (e.g. msg.sender.balance) is a fixed value that will NOT change between transactions. This value is determined by the following config option:

balanceAddr: 0xffffffff
Controlling the amount of ether in contracts
Another approach to handle ether will be allow the testing contract to receive certain amount and then use it to send it.

contract A {
    C internal c;

    constructor() public payable {
        require(msg.value == 12000);
        c = new C();
    }

    function payToContract(uint256 toPay) public {
        toPay = toPay % (address(this).balance + 1);
        c.pay{ value: toPay }();
    }

    function echidna_C_has_some_value() public returns (bool) {
        return (address(c).balance != 12000);
    }
}

contract C {
    function pay() public payable {
        require(msg.value == 12000);
    }
}
However, if we run this directly with echidna, it will fail:

$ echidna balanceContract.sol
...
echidna: Deploying the contract 0x00a329c0648769A73afAc7F9381E08FB43dBEA72 failed (revert, out-of-gas, sending ether to an non-payable constructor, etc.):
We need to define the amount to send during the contract creation:

balanceContract: 12000
We can re-run echidna, using that config file, to obtain the expected result:

$ echidna balanceContract.sol --config balanceContract.yaml
...
echidna_C_has_some_value: failed!💥
  Call sequence:
    payToContract(12000)
Summary: Working with ether
Echidna has two options for using ether during a fuzzing campaign.

maxValue to set the max amount of ether per transaction
balanceContract to set the initial amount of ether that the testing contract receives in the constructor.

How to Write Good Properties Step by Step
Table of contents:

How to Write Good Properties Step by Step
Introduction
A First Approach
Enhancing Postcondition Checks
Combining Properties
Final Considerations
Summary: How to Write Good Properties
Introduction
In this short tutorial, we will detail some ideas for writing interesting or useful properties using Echidna. At each step, we will iteratively improve our properties.

A First Approach
One of the simplest properties to write using Echidna is to throw an assertion when some function is expected to revert or return.

Let's suppose we have a contract interface like the one below:

interface DeFi {
    ERC20 t;

    function getShares(address user) external returns (uint256);

    function createShares(uint256 val) external returns (uint256);

    function depositShares(uint256 val) external;

    function withdrawShares(uint256 val) external;

    function transferShares(address to) external;
}
In this example, users can deposit tokens using depositShares, mint shares using createShares, withdraw shares using withdrawShares, transfer all shares to another user using transferShares, and get the number of shares for any account using getShares. We will start with very basic properties:

contract Test {
    DeFi defi;
    ERC20 token;

    constructor() {
        defi = DeFi(...);
        token.mint(address(this), ...);
    }

    function getShares_never_reverts() public {
        (bool b,) = defi.call(abi.encodeWithSignature("getShares(address)", address(this)));
        assert(b);
    }

    function depositShares_never_reverts(uint256 val) public {
        if (token.balanceOf(address(this)) >= val) {
            (bool b,) = defi.call(abi.encodeWithSignature("depositShares(uint256)", val));
            assert(b);
        }
    }

    function withdrawShares_never_reverts(uint256 val) public {
        if (defi.getShares(address(this)) >= val) {
            (bool b,) = defi.call(abi.encodeWithSignature("withdrawShares(uint256)", val));
            assert(b);
        }
    }

    function depositShares_can_revert(uint256 val) public {
        if (token.balanceOf(address(this)) < val) {
            (bool b,) = defi.call(abi.encodeWithSignature("depositShares(uint256)", val));
            assert(!b);
        }
    }

    function withdrawShares_can_revert(uint256 val) public {
        if (defi.getShares(address(this)) < val) {
            (bool b,) = defi.call(abi.encodeWithSignature("withdrawShares(uint256)", val));
            assert(!b);
        }
    }
}
After you have written your first version of properties, run Echidna to make sure they work as expected. During this tutorial, we will improve them step by step. It is strongly recommended to run the fuzzer at each step to increase the probability of detecting any potential issues.

Perhaps you think these properties are too low level to be useful, particularly if the code has good coverage in terms of unit tests. But you will be surprised how often an unexpected revert or return uncovers a complex and severe issue. Moreover, we will see how these properties can be improved to cover more complex post-conditions.

Before we continue, we will improve these properties using try/catch. The use of a low-level call forces us to manually encode the data, which can be error-prone (an error will always cause calls to revert). Note, this will only work if the codebase is using solc 0.6.0 or later:

function depositShares_never_reverts(uint256 val) public {
    if (token.balanceOf(address(this)) >= val) {
        try defi.depositShares(val) {
            /* not reverted */
        } catch {
            assert(false);
        }
    }
}

function depositShares_can_revert(uint256 val) public {
    if (token.balanceOf(address(this)) < val) {
        try defi.depositShares(val) {
            assert(false);
        } catch {
            /* reverted */
        }
    }
}
Enhancing Postcondition Checks
If the previous properties are passing, this means that the pre-conditions are good enough, however the post-conditions are not very precise. Avoiding reverts doesn't mean that the contract is in a valid state. Let's add some basic preconditions:

function depositShares_never_reverts(uint256 val) public {
    if (token.balanceOf(address(this)) >= val) {
        try defi.depositShares(val) {
            /* not reverted */
        } catch {
            assert(false);
        }
        assert(defi.getShares(address(this)) > 0);
    }
}

function withdrawShares_never_reverts(uint256 val) public {
    if (defi.getShares(address(this)) >= val) {
        try defi.withdrawShares(val) {
            /* not reverted */
        } catch {
            assert(false);
        }
        assert(token.balanceOf(address(this)) > 0);
    }
}
Hmm, it looks like it is not that easy to specify the value of shares or tokens obtained after each deposit or withdrawal. At least we can say that we must receive something, right?

Combining Properties
In this generic example, it is unclear if there is a way to calculate how many shares or tokens we should receive after executing the deposit or withdraw operations. Of course, if we have that information, we should use it. In any case, what we can do here is to combine these two properties into a single one to be able check more precisely its preconditions.

function deposit_withdraw_shares_never_reverts(uint256 val) public {
    uint256 original_balance = token.balanceOf(address(this));
    if (original_balance >= val) {
        try defi.depositShares(val) {
            /* not reverted */
        } catch {
            assert(false);
        }
        uint256 shares = defi.getShares(address(this));
        assert(shares > 0);
        try defi.withdrawShares(shares) {
            /* not reverted */
        } catch {
            assert(false);
        }
        assert(token.balanceOf(address(this)) == original_balance);
    }
}
The resulting property checks that calls to deposit or withdraw shares will never revert and once they execute, the original number of tokens remains the same. Keep in mind that this property should consider fees and any tolerated loss of precision (e.g. when the computation requires a division).

Final Considerations
Two important considerations for this example:

We want Echidna to spend most of the execution exploring the contract to test. So, in order to make the properties more efficient, we should avoid dead branches where there is nothing to do. That's why we can improve depositShares_never_reverts to use:

function depositShares_never_reverts(uint256 val) public {
    if (token.balanceOf(address(this)) > 0) {
        val = val % (token.balanceOf(address(this)) + 1);
        try defi.depositShares(val) { /* not reverted */ }
        catch {
            assert(false);
        }
        assert(defi.getShares(address(this)) > 0);
    } else {
        ... // code to test depositing zero tokens
    }
}
Additionally, combining properties does not mean that we will have to remove simpler ones. For instance, if we want to write withdraw_deposit_shares_never_reverts, in which we reverse the order of operations (withdraw and then deposit, instead of deposit and then withdraw), we will have to make sure defi.getShares(address(this)) can be positive. An easy way to do it is to keep depositShares_never_reverts, since this code allows Echidna to deposit tokens from address(this) (otherwise, this is impossible).

Summary: How to Write Good Properties
It is usually a good idea to start writing simple properties first and then improving them to make them more precise and easier to read. At each step, you should run a short fuzzing campaign to make sure they work as expected and try to catch issues early during the development of your smart contracts.

Collecting, Visualizing, and Modifying an Echidna Corpus
Table of contents:

Introduction
Collecting a corpus
Seeding a corpus
Introduction
In this guide, we will explore how to collect and use a corpus of transactions with Echidna. Our target is the following smart contract, magic.sol:

contract C {
    bool value_found = false;

    function magic(uint256 magic_1, uint256 magic_2, uint256 magic_3, uint256 magic_4) public {
        require(magic_1 == 42);
        require(magic_2 == 129);
        require(magic_3 == magic_4 + 333);
        value_found = true;
        return;
    }

    function echidna_magic_values() public view returns (bool) {
        return !value_found;
    }
}
This small example requires Echidna to find specific values to change a state variable. While this is challenging for a fuzzer (it is advised to use a symbolic execution tool like Manticore), we can still employ Echidna to collect corpus during this fuzzing campaign.

Collecting a corpus
To enable corpus collection, first, create a corpus directory:

mkdir corpus-magic
Next, create an Echidna configuration file called config.yaml:

corpusDir: "corpus-magic"
Now, run the tool and inspect the collected corpus:

echidna magic.sol --config config.yaml
Echidna is still unable to find the correct magic value. To understand where it gets stuck, review the corpus-magic/covered.*.txt file:

  1 | *   | contract C {
  2 |     |     bool value_found = false;
  3 |     |
  4 | *   |     function magic(uint256 magic_1, uint256 magic_2, uint256 magic_3, uint256 magic_4) public {
  5 | *r  |         require(magic_1 == 42);
  6 | *r  |         require(magic_2 == 129);
  7 | *r  |         require(magic_3 == magic_4 + 333);
  8 |     |         value_found = true;
  9 |     |         return;
 10 |     |     }
 11 |     |
 12 |     |     function echidna_magic_values() public returns (bool) {
 13 |     |         return !value_found;
 14 |     |     }
 15 |     | }
The label r on the left of each line indicates that Echidna can reach these lines, but they result in a revert. As you can see, the fuzzer gets stuck at the last require.

To find a workaround, let's examine the collected corpus. For instance, one of these files contains:

[
    {
        "_gas'": "0xffffffff",
        "_delay": ["0x13647", "0xccf6"],
        "_src": "00a329c0648769a73afac7f9381e08fb43dbea70",
        "_dst": "00a329c0648769a73afac7f9381e08fb43dbea72",
        "_value": "0x0",
        "_call": {
            "tag": "SolCall",
            "contents": [
                "magic",
                [
                    {
                        "contents": [
                            256,
                            "93723985220345906694500679277863898678726808528711107336895287282192244575836"
                        ],
                        "tag": "AbiUInt"
                    },
                    {
                        "contents": [256, "334"],
                        "tag": "AbiUInt"
                    },
                    {
                        "contents": [
                            256,
                            "68093943901352437066264791224433559271778087297543421781073458233697135179558"
                        ],
                        "tag": "AbiUInt"
                    },
                    {
                        "tag": "AbiUInt",
                        "contents": [256, "332"]
                    }
                ]
            ]
        },
        "_gasprice'": "0xa904461f1"
    }
]
This input will not trigger the failure in our property. In the next step, we will show how to modify it for that purpose.

Seeding a corpus
To handle the magic function, Echidna needs some assistance. We will copy and modify the input to utilize appropriate parameters:

cp corpus-magic/coverage/2712688662897926208.txt corpus-magic/coverage/new.txt
Modify new.txt to call magic(42,129,333,0). Now, re-run Echidna:

echidna magic.sol --config config.yaml
...
echidna_magic_values: failed!💥
  Call sequence:
    magic(42,129,333,0)

Unique instructions: 142
Unique codehashes: 1
Seed: -7293830866560616537

This time, the property fails immediately. We can verify that another covered.*.txt file is created, showing a different trace (labeled with *) that Echidna executed, which ended with a return at the end of the magic function.

  1 | *   | contract C {
  2 |     |     bool value_found = false;
  3 |     |
  4 | *   |     function magic(uint256 magic_1, uint256 magic_2, uint256 magic_3, uint256 magic_4) public {
  5 | *r  |         require(magic_1 == 42);
  6 | *r  |         require(magic_2 == 129);
  7 | *r  |         require(magic_3 == magic_4 + 333);
  8 | *   |         value_found = true;
  9 |     |         return;
 10 |     |     }
 11 |     |
 12 |     |     function echidna_magic_values() public returns (bool) {
 13 |     |         return !value_found;
 14 |     |     }
 15 |     | }

 Finding Local Maximums Using Optimization Mode
Table of Contents:

Finding Local Maximums Using Optimization Mode
Introduction
Optimizing with Echidna
Introduction
In this tutorial, we will explore how to perform function optimization using Echidna. Please ensure you have updated Echidna to version 2.0.5 or greater before proceeding.

Optimization mode is an experimental feature that enables the definition of a special function, taking no arguments and returning an int256. Echidna will attempt to find a sequence of transactions to maximize the value returned:

function echidna_opt_function() public view returns (int256) {
    // If it reverts, Echidna will assume it returned type(int256).min
    return value;
}
Optimizing with Echidna
In this example, the target is the following smart contract (opt.sol):

contract TestDutchAuctionOptimization {
    int256 maxPriceDifference;

    function setMaxPriceDifference(uint256 startPrice, uint256 endPrice, uint256 startTime, uint256 endTime) public {
        if (endTime < (startTime + 900)) revert();
        if (startPrice <= endPrice) revert();

        uint256 numerator = (startPrice - endPrice) * (block.timestamp - startTime);
        uint256 denominator = endTime - startTime;
        uint256 stepDecrease = numerator / denominator;
        uint256 currentAuctionPrice = startPrice - stepDecrease;

        if (currentAuctionPrice < endPrice) {
            maxPriceDifference = int256(endPrice - currentAuctionPrice);
        }
        if (currentAuctionPrice > startPrice) {
            maxPriceDifference = int256(currentAuctionPrice - startPrice);
        }
    }

    function echidna_opt_price_difference() public view returns (int256) {
        return maxPriceDifference;
    }
}
This small example directs Echidna to maximize a specific price difference given certain preconditions. If the preconditions are not met, the function will revert without changing the actual value.

To run this example:

echidna opt.sol --test-mode optimization --test-limit 100000 --seq-len 1 --corpus-dir corpus --shrink-limit 50000
...
echidna_opt_price_difference: max value: 1076841

  Call sequence, shrinking (42912/50000):
    setMaxPriceDifference(1349752405,1155321,609,1524172858) Time delay: 603902 seconds Block delay: 21

The resulting max value is not unique; running a longer campaign will likely yield a larger value.

Regarding the command line, optimization mode is enabled using --test-mode optimization. Additionally, we included the following tweaks:

Use only one transaction (as we know the function is stateless).
Use a large shrink limit to obtain a better value during input complexity minimization.
Each time Echidna is executed using the corpus directory, the last input producing the maximum value should be reused from the reproducers directory:

echidna opt.sol --test-mode optimization --test-limit 100000 --seq-len 1 --corpus-dir corpus --shrink-limit 50000
Loaded total of 1 transactions from corpus/reproducers/
Loaded total of 9 transactions from corpus/coverage/
Analyzing contract: /home/g/Code/echidna/opt.sol:TestDutchAuctionOptimization
echidna_opt_price_difference: max value: 1146878

  Call sequence:
    setMaxPriceDifference(1538793592,1155321,609,1524172858) Time delay: 523701 seconds Block delay: 49387

    Identifying High Gas Consumption Transactions
Table of contents:

Identifying high gas consumption transactions
Introduction
Measuring Gas Consumption
Running Echidna
Excluding Gas-Reducing Calls
Summary: Identifying high gas consumption transactions
Introduction
This guide demonstrates how to identify transactions with high gas consumption using Echidna. The target is the following smart contract (gas.sol):

contract C {
    uint256 state;

    function expensive(uint8 times) internal {
        for (uint8 i = 0; i < times; i++) {
            state = state + i;
        }
    }

    function f(uint256 x, uint256 y, uint8 times) public {
        if (x == 42 && y == 123) {
            expensive(times);
        } else {
            state = 0;
        }
    }

    function echidna_test() public returns (bool) {
        return true;
    }
}
The expensive function can have significant gas consumption.

Currently, Echidna always requires a property to test - in this case, echidna_test always returns true. We can run Echidna to verify this:

echidna gas.sol
...
echidna_test: passed! 🎉

Seed: 2320549945714142710
Measuring Gas Consumption
To enable Echidna's gas consumption feature, create a configuration file gas.yaml:

estimateGas: true
In this example, we'll also reduce the size of the transaction sequence for easier interpretation:

seqLen: 2
estimateGas: true
Running Echidna
With the configuration file created, we can run Echidna as follows:

echidna gas.sol --config config.yaml
...
echidna_test: passed! 🎉

f used a maximum of 1333608 gas
  Call sequence:
    f(42,123,249) Gas price: 0x10d5733f0a Time delay: 0x495e5 Block delay: 0x88b2

Unique instructions: 157
Unique codehashes: 1
Seed: -325611019680165325
The displayed gas is an estimation provided by HEVM.
Excluding Gas-Reducing Calls
The tutorial on filtering functions to call during a fuzzing campaign demonstrates how to remove certain functions during testing. This can be crucial for obtaining accurate gas estimates. Consider the following example (example/pushpop.sol):

contract C {
    address[] addrs;

    function push(address a) public {
        addrs.push(a);
    }

    function pop() public {
        addrs.pop();
    }

    function clear() public {
        addrs.length = 0;
    }

    function check() public {
        for (uint256 i = 0; i < addrs.length; i++)
            for (uint256 j = i + 1; j < addrs.length; j++) if (addrs[i] == addrs[j]) addrs[j] = address(0);
    }

    function echidna_test() public returns (bool) {
        return true;
    }
}
With this config.yaml, Echidna can call all functions but won't easily identify transactions with high gas consumption:

echidna pushpop.sol --config config.yaml
...
pop used a maximum of 10746 gas
...
check used a maximum of 23730 gas
...
clear used a maximum of 35916 gas
...
push used a maximum of 40839 gas
This occurs because the cost depends on the size of addrs, and random calls tend to leave the array almost empty. By blacklisting pop and clear, we obtain better results (blacklistpushpop.yaml):

estimateGas: true
filterBlacklist: true
filterFunctions: ["C.pop()", "C.clear()"]
echidna pushpop.sol --config config.yaml
...
push used a maximum of 40839 gas
...
check used a maximum of 1484472 gas
Summary: Identifying high gas consumption transactions
Echidna can identify transactions with high gas consumption using the estimateGas configuration option:

estimateGas: true
echidna contract.sol --config config.yaml
...
After completing the fuzzing campaign, Echidna will report a sequence with the maximum gas consumption for each function.

Fuzzing Smart Contracts at Scale with Echidna
In this tutorial, we will review how to create a dedicated server for fuzzing smart contracts using Echidna.

Workflow:
Install and set up a dedicated server
Begin a short fuzzing campaign
Initiate a continuous fuzzing campaign
Add properties, check coverage, and modify the code if necessary
Conclude the campaign
1. Install and set up a dedicated server
First, obtain a dedicated server with at least 32 GB of RAM and as many cores as possible. Start by creating a user for the fuzzing campaign. Only use the root account to create an unprivileged user:

# adduser echidna
# usermod -aG sudo echidna
Then, using the echidna user, install some basic dependencies:

sudo apt install unzip python3-pip
Next, install everything necessary to build your smart contract(s) as well as slither and echidna-parade. For example:

pip3 install solc-select
solc-select install all
pip3 install slither_analyzer
pip3 install echidna_parade
Add $PATH=$PATH:/home/echidna/.local/bin at the end of /home/echidna/.bashrc.

Afterward, install Echidna. The easiest way is to download the latest precompiled Echidna release, uncompress it, and move it to /home/echidna/.local/bin:

wget "https://github.com/crytic/echidna/releases/download/v2.0.0/echidna-test-2.0.0-Ubuntu-18.04.tar.gz"
tar -xf echidna-test-2.0.0-Ubuntu-18.04.tar.gz
mv echidna-test /home/echidna/.local/bin
2. Begin a short fuzzing campaign
Select a contract to test and provide initialization if needed. It does not have to be perfect; begin with some basic items and iterate over the results. Before starting this campaign, modify your Echidna config to define a corpus directory to use. For instance:

corpusDir: "corpus-exploration"
This directory will be automatically created, but since we are starting a new campaign, please remove the corpus directory if it was created by a previous Echidna campaign. If you don't have any properties to test, you can use:

testMode: exploration
to allow Echidna to run without any properties.

We will start a brief Echidna run (5 minutes) to check that everything looks fine. To do that, use the following config:

testLimit: 100000000000
timeout: 300 # 5 minutes
Once it runs, check the coverage file located in corpus-exploration/covered.*.txt. If the initialization is incorrect, clear the corpus-exploration directory and restart the campaign.

3. Initiate a continuous fuzzing campaign
When satisfied with the first iteration of the initialization, we can start a "continuous campaign" for exploration and testing using echidna-parade. Before starting, double-check your config file. For instance, if you added properties, do not forget to remove benchmarkMode.

echidna-parade is a tool used to launch multiple Echidna instances simultaneously while keeping track of each corpus. Each instance will be configured to run for a specific duration, with different parameters, to maximize the chance of reaching new code.

We will demonstrate this with an example, where:

the initial corpus is empty
the base config file is exploration.yaml
the initial instance will run for 3600 seconds (1 hour)
each "generation" will run for 1800 seconds (30 minutes)
the campaign will run in continuous mode (if the timeout is -1, it means run indefinitely)
there will be 8 Echidna instances per generation. Adjust this according to the number of available cores, but avoid using all of your cores if you do not want to overload your server
the target contract is named C
the file containing the contract is test.sol
Finally, we will log the stdout and stderr in parade.log and parade.err and fork the process to let it run indefinitely.

echidna-parade test.sol --config exploration.yaml --initial_time 3600 --gen_time 1800 --timeout -1 --ncores 8 --contract C > parade.log 2> parade.err &
After running this command, exit the shell to avoid accidentally killing it if your connection fails.

4. Add more properties, check coverage, and modify the code if necessary
In this step, we can add more properties while Echidna explores the contracts. Keep in mind that you should avoid changing the contracts' ABI (otherwise, the quality of the corpus will degrade).

Additionally, we can tweak the code to improve coverage, but before starting, we need to know how to monitor our fuzzing campaign. We can use this command:

watch "grep 'COLLECTING NEW COVERAGE' parade.log | tail -n 30"
When new coverage is found, you will see something like this:

COLLECTING NEW COVERAGE: parade.181140/gen.30.10/corpus/coverage/-3538310549422809236.txt
COLLECTING NEW COVERAGE: parade.181140/gen.35.9/corpus/coverage/5960152130200926175.txt
COLLECTING NEW COVERAGE: parade.181140/gen.35.10/corpus/coverage/3416698846701985227.txt
COLLECTING NEW COVERAGE: parade.181140/gen.36.6/corpus/coverage/-3997334938716772896.txt
COLLECTING NEW COVERAGE: parade.181140/gen.37.7/corpus/coverage/323061126212903141.txt
COLLECTING NEW COVERAGE: parade.181140/gen.37.6/corpus/coverage/6733481703877290093.txt
You can verify the corresponding covered file, such as parade.181140/gen.37.6/corpus/covered.1615497368.txt.

For examples on how to help Echidna improve its coverage, please review the improving coverage tutorial.

To monitor failed properties, use this command:

watch "grep 'FAIL' parade.log | tail -n 30"
When failed properties are found, you will see something like this:

NEW FAILURE: assertion in f: failed!💥
parade.181140/gen.179.0 FAILED
parade.181140/gen.179.3 FAILED
parade.181140/gen.180.2 FAILED
parade.181140/gen.180.4 FAILED
parade.181140/gen.180.3 FAILED
...
5. Conclude the campaign
When satisfied with the coverage results, you can terminate the continuous campaign using:

killall echidna-parade echidna

How to Test Bytecode-Only Contracts
Table of contents:

How to Test Bytecode-Only Contracts
Introduction
Proxy Pattern
Running Echidna
Target Source Code
Differential Fuzzing
Generic Proxy Code
Summary: Testing Contracts Without Source Code
Introduction
In this tutorial, you'll learn how to fuzz a contract without any provided source code. The technique can also be used to perform differential fuzzing (i.e., compare multiple implementations) between a Solidity contract and a Vyper contract.

Consider the following bytecode:

608060405234801561001057600080fd5b506103e86000803373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff168152602001908152602001600020819055506103e86001819055506101fa8061006e6000396000f3fe608060405234801561001057600080fd5b50600436106100415760003560e01c806318160ddd1461004657806370a0823114610064578063a9059cbb146100bc575b600080fd5b61004e61010a565b6040518082815260200191505060405180910390f35b6100a66004803603602081101561007a57600080fd5b81019080803573ffffffffffffffffffffffffffffffffffffffff169060200190929190505050610110565b6040518082815260200191505060405180910390f35b610108600480360360408110156100d257600080fd5b81019080803573ffffffffffffffffffffffffffffffffffffffff16906020019092919080359060200190929190505050610128565b005b60015481565b60006020528060005260406000206000915090505481565b806000803373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff16815260200190815260200160002060008282540392505081905550806000808473ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff16815260200190815260200160002060008282540192505081905550505056fe
For which we only know the ABI:

interface Target {
    function totalSupply() external returns (uint256);

    function balanceOf(address) external returns (uint256);

    function transfer(address, uint256) external;
}
We want to test if it is possible to have more tokens than the total supply.

Proxy Pattern
Since we don't have the source code, we can't directly add the property to the contract. Instead, we'll use a proxy contract:

interface Target {
    function totalSupply() external returns (uint256);

    function balanceOf(address) external returns (uint256);

    function transfer(address, uint256) external;
}

contract TestBytecodeOnly {
    Target target;

    constructor() {
        address targetAddress;
        // init bytecode
        bytes
            memory targetCreationBytecode = hex"608060405234801561001057600080fd5b506103e86000803373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff168152602001908152602001600020819055506103e86001819055506101fa8061006e6000396000f3fe608060405234801561001057600080fd5b50600436106100415760003560e01c806318160ddd1461004657806370a0823114610064578063a9059cbb146100bc575b600080fd5b61004e61010a565b6040518082815260200191505060405180910390f35b6100a66004803603602081101561007a57600080fd5b81019080803573ffffffffffffffffffffffffffffffffffffffff169060200190929190505050610110565b6040518082815260200191505060405180910390f35b610108600480360360408110156100d257600080fd5b81019080803573ffffffffffffffffffffffffffffffffffffffff16906020019092919080359060200190929190505050610128565b005b60015481565b60006020528060005260406000206000915090505481565b806000803373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff16815260200190815260200160002060008282540392505081905550806000808473ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff16815260200190815260200160002060008282540192505081905550505056fe";

        uint256 size = targetCreationBytecode.length;

        assembly {
            targetAddress := create(0, add(targetCreationBytecode, 0x20), size) // Skip the 32 bytes encoded length.
        }

        target = Target(targetAddress);
    }

    function transfer(address to, uint256 amount) public {
        target.transfer(to, amount);
    }

    function echidna_test_balance() public returns (bool) {
        return target.balanceOf(address(this)) <= target.totalSupply();
    }
}
The proxy:

Deploys the bytecode in its constructor
Has one function that calls the target's transfer function
Has one Echidna property target.balanceOf(address(this)) <= target.totalSupply()
Running Echidna
echidna bytecode_only.sol --contract TestBytecodeOnly
echidna_test_balance: failed!💥
  Call sequence:
    transfer(0x0,1002)
Here, Echidna found that by calling transfer(0, 1002) anyone can mint tokens.

Target Source Code
The actual source code of the target is:

contract C {
    mapping(address => uint256) public balanceOf;
    uint256 public totalSupply;

    constructor() public {
        balanceOf[msg.sender] = 1000;
        totalSupply = 1000;
    }

    function transfer(address to, uint256 amount) public {
        balanceOf[msg.sender] -= amount;
        balanceOf[to] += amount;
    }
}
Echidna correctly found the bug: lack of overflow checks in transfer.

Differential Fuzzing
Consider the following Vyper and Solidity contracts:

@view
@external
def my_func(a: uint256, b: uint256, c: uint256) -> uint256:
    return a * b / c
contract SolidityVersion {
    function my_func(uint256 a, uint256 b, uint256 c) public view {
        return (a * b) / c;
    }
}
We can test that they always return the same values using the proxy pattern:

interface Target {
    function my_func(uint256, uint256, uint256) external returns (uint256);
}

contract SolidityVersion {
    Target target;

    constructor() public {
        address targetAddress;

        // vyper bytecode
        bytes
            memory targetCreationBytecode = hex"61007756341561000a57600080fd5b60043610156100185761006d565b600035601c52630ff198a3600051141561006c57600435602435808202821582848304141761004657600080fd5b80905090509050604435808061005b57600080fd5b82049050905060005260206000f350005b5b60006000fd5b61000461007703610004600039610004610077036000f3";

        uint256 size = targetCreationBytecode.length;

        assembly {
            targetAddress := create(0, add(targetCreationBytecode, 0x20), size) // Skip the 32 bytes encoded length.
        }
        target = Target(targetAddress);
    }

    function test(uint256 a, uint256 b, uint256 c) public returns (bool) {
        assert(my_func(a, b, c) == target.my_func(a, b, c));
    }

    function my_func(uint256 a, uint256 b, uint256 c) internal view returns (uint256) {
        return (a * b) / c;
    }
}
Here we run Echidna with the assertion mode:

echidna  vyper.sol --config config.yaml --contract SolidityVersion --test-mode assertion
assertion in test: passed! 🎉
Generic Proxy Code
Adapt the following code to your needs:

interface Target {
    // public/external functions
}

contract TestBytecodeOnly {
    Target target;

    constructor() public {
        address targetAddress;
        // init bytecode
        bytes memory targetCreationBytecode = hex"";

        uint256 size = targetCreationBytecode.length;

        assembly {
            targetAddress := create(0, add(targetCreationBytecode, 0x20), size) // Skip the 32 bytes encoded length.
        }
        target = Target(targetAddress);
    }

    // Add helper functions to call the target's functions from the proxy

    function echidna_test() public returns (bool) {
        // The property to test
    }
}
Summary: Testing Contracts Without Source Code
Echidna can fuzz contracts without source code using a proxy contract. This technique can also be used to compare implementations written in Solidity and Vyper.

How and when to use cheat codes
Table of contents:

How and when to use cheat codes
Introduction
Cheat codes available in Echidna
Risks of cheat codes
Introduction
When testing smart contracts in Solidity itself, it can be helpful to use cheat codes in order to overcome some of the limitations of the EVM/Solidity. Cheat codes are special functions that allow to change the state of the EVM in ways that are not posible in production. These were introduced by Dapptools in hevm and adopted (and expanded) in other projects such as Foundry.

Cheat codes available in Echidna
Echidna supports all cheat codes that are available in hevm. These are documented here: https://hevm.dev/controlling-the-unit-testing-environment.html#cheat-codes. If a new cheat code is added in the future, Echidna only needs to update the hevm version and everything should work out of the box.

As an example, the prank cheat code is able to set the msg.sender address in the context of the next external call:

interface IHevm {
    function prank(address) external;
}

contract TestPrank {
  address constant HEVM_ADDRESS = 0x7109709ECfa91a80626fF3989D68f67F5b1DD12D;
  IHevm hevm = IHevm(HEVM_ADDRESS);
  Contract c = ...

  function prankContract() public payable {
    hevm.prank(address(0x42424242);
    c.f(); // `c` will be called with `msg.sender = 0x42424242`
  }
}
A specific example on the use of sign cheat code is available here in our documentation.

Risks of cheat codes
While we provide support for the use of cheat codes, these should be used responsibly. Consider that:

Cheat codes can break certain assumptions in Solidity. For example, the compiler assumes that block.number is constant during a transaction. There are reports of the optimizer interfering with (re)computation of the block.number or block.timestamp, which can generate incorrect tests when using cheat codes.

Cheat codes can introduce false positives on the testing. For instance, using prank to simulate calls from a contract can allow transactions that are not possible in the blockchain.

Using too many cheat codes:

can be confusing or error-prone. Certain cheat code like prank allow to change caller in the next external call: It can be difficult to follow, in particular if it is used in internal functions or modifiers.
will create a dependency of your code with the particular tool or cheat code implementation: It can cause produce migrations to other tools or reusing the test code to be more difficult than expected.

Using HEVM Cheats To Test Permit
Introduction
EIP 2612 introduces the function permit(address owner, address spender, uint256 value, uint256 deadline, uint8 v, bytes32 r, bytes32 s) to the ERC20 ABI. This function takes in signature parameters generated through ECDSA, combined with the EIP 712 standard for typed data hashing, and recovers the author of the signature through ecrecover(). It then sets allowances[owner][spender] to value.

Uses
This method presents a new way of allocating allowances, as signatures can be computed off-chain and passed to a contract. It allows a relayer to pay the entire gas fee of the permit transaction in exchange for a fee, enabling completely gasless transactions for a user. Furthermore, this removes the typical approve() -> transferFrom() pattern that forces users to send two transactions instead of just one through this new method.

Note that for the permit function to work, a valid signature is needed. This example will demonstrate how we can use hevm's sign cheatcode to sign data with a private key. More generally, you can use this cheatcode to test anything that requires valid signatures.

Example
We use Solmate’s implementation of the ERC20 standard that includes the permit function. Observe that there are also values for the PERMIT_TYPEHASH and a mapping(address -> uint256) public nonces. The former is part of the EIP712 standard, and the latter is used to prevent signature replay attacks.

In our TestDepositWithPermit contract, we need to have the signature signed by an owner for validation. To accomplish this, we can use hevm’s sign cheatcode, which takes in a message and a private key and creates a valid signature. For this example, we use the private key 0x02, and the following signed message representing the permit signature following the EIP 712:

keccak256(
    abi.encodePacked(
        "\x19\x01",
        asset.DOMAIN_SEPARATOR(),
        keccak256(
            abi.encode(
                keccak256("Permit(address owner,address spender,uint256 value,uint256 nonce,uint256 deadline)"),
                owner,
                spender,
                assetAmount,
                asset.nonces(owner),
                block.timestamp
            )
        )
    )
);
The helper function getSignature(address owner, address spender, uint256 assetAmount) returns a valid signature generated via the sign cheatcode. Note that the sign cheatcode exposes the private key, so it is best to use dummy keys when testing. Our keypair data was taken from this site. To test the signature, we will mint a random amount to the OWNER address, the address corresponding to the private key 0x02, which was the signer of the permit signature. We then check whether we can use that signature to transfer the owner’s tokens to ourselves.

First, we call permit() on our Mock ERC20 token with the signature generated in getSignature(), and then call transferFrom(). If our permit request and transfer are successful, our balance of the mock ERC20 should increase by the amount permitted, and the OWNER's balance should decrease as well. For simplicity, we'll transfer all the minted tokens so that the OWNER's balance will be 0, and our balance will be amount.

Code
The complete example code can be found here.

End-to-End Testing with Echidna (Part I)
When smart contracts require complex initialization and the time to do so is short, we want to avoid manually recreating a deployment for a fuzzing campaign with Echidna. That's why we have a new approach for testing using Echidna based on the deployments and execution of tests directly from Ganache.

Requirements:
This approach needs a smart contract project with the following constraints:

It should use Solidity; Vyper is not supported since Slither/Echidna is not very effective at running these (e.g. no AST is included).
It should have tests or at least a complete deployment script.
It should work with Slither. If it fails, please report the issue.
For this tutorial, we used the Drizzle-box example.

Getting Started:
Before starting, make sure you have the latest releases from Echidna and Etheno installed.

Then, install the packages to compile the project:

git clone https://github.com/truffle-box/drizzle-box
cd drizzle-box
npm i truffle
If ganache is not installed, add it manually. In our example, we will run:

npm -g i ganache
Other projects using Yarn will require:

yarn global add ganache
Ensure that $ ganache --version outputs ganache v7.3.2 or greater.

It is also important to select one test script from the available tests. Ideally, this test will deploy all (or most) contracts, including mock/test ones. For this example, we are going to examine the SimpleStorage contract:

contract SimpleStorage {
    event StorageSet(string _message);

    uint256 public storedData;

    function set(uint256 x) public {
        storedData = x;

        emit StorageSet("Data stored successfully!");
    }
}
This small contract allows the storedData state variable to be set. As expected, we have a unit test that deploys and tests this contract (simplestorage.js):

const SimpleStorage = artifacts.require("SimpleStorage");

contract("SimpleStorage", (accounts) => {
    it("...should store the value 89.", async () => {
        const simpleStorageInstance = await SimpleStorage.deployed();

        // Set value of 89
        await simpleStorageInstance.set(89, { from: accounts[0] });

        // Get stored value
        const storedData = await simpleStorageInstance.storedData.call();

        assert.equal(storedData, 89, "The value 89 was not stored.");
    });
});
Capturing Transactions
Before starting to write interesting properties, it is necessary to collect an Etheno trace to replay it inside Echidna:

First, start Etheno:

etheno --ganache --ganache-args="--miner.blockGasLimit 10000000" -x init.json
By default, the following Ganache arguments are set via Etheno:

-d: Ganache will use a pre-defined, deterministic seed to create all accounts.
--chain.allowUnlimitedContractSize: Allows unlimited contract sizes while debugging. This is set so that there is no size limitation on the contracts that are going to be deployed.
-p <port_num>: The port_num will be set to (1) the value of --ganache-port or (2) Etheno will choose the smallest port number higher than the port number on which Etheno’s JSON RPC server is running.
NOTE: If you are using Docker to run Etheno, the commands should be:

docker run -it -p 8545:8545 -v ~/etheno:/home/etheno/ trailofbits/etheno
(you will now be working within the Docker instance)
etheno --ganache --ganache-args="--miner.blockGasLimit 10000000" -x init.json
The -p in the first command publishes (i.e., exposes) port 8545 from inside the Docker container out to port 8545 on the host.
The -v in the first command maps a directory from inside the Docker container to one outside the Docker container. After Etheno exits, the init.json file will now be in the ~/etheno folder on the host.
Note that if the deployment fails to complete successfully due to a ProviderError: exceeds block gas limit exception, increasing the --miner.blockGasLimit value can help. This is especially helpful for large contract deployments. Learn more about the various Ganache command-line arguments that can be set by clicking here.

Additionally, if Etheno fails to produce any output, it may have failed to execute ganache under-the-hood. Check if ganache (with the associated command-line arguments) can be executed correctly from your terminal without the use of Etheno.

Meanwhile, in another terminal, run one test or the deployment process. How to run it depends on how the project was developed. For instance, for Truffle, use:

truffle test test/test.js
For Buidler:

buidler test test/test.js --network localhost
In the Drizzle example, we will run:

truffle test test/simplestorage.js --network develop.
After Etheno finishes, gently kill it using Ctrl+C (or Command+C on Mac). It will save the init.json file. If your test fails for some reason, or you want to run a different one, restart Etheno and re-run the test.

Writing and Running a Property
Once we have a JSON file with saved transactions, we can verify that the SimpleStorage contract is deployed at 0x871DD7C2B4b25E1Aa18728e9D5f2Af4C4e431f5c. We can easily write a contract in contracts/crytic/E2E.sol with a simple property to test it:

import "../SimpleStorage.sol";

contract E2E {
    SimpleStorage st = SimpleStorage(0x871DD7C2B4b25E1Aa18728e9D5f2Af4C4e431f5c);

    function crytic_const_storage() public returns (bool) {
        return st.storedData() == 89;
    }
}
For large, multi-contract deployments, using console.log to print out the deployed contract addresses can be valuable in quickly setting up the Echidna testing contract.

This simple property checks if the stored data remains constant. To run it, you will need the following Echidna config file (echidna.yaml):

prefix: crytic_
initialize: init.json
allContracts: true
cryticArgs: ["--truffle-build-directory", "app/src/contracts/"] # needed by Drizzle
Then, running Echidna shows the results immediately:

echidna . --contract E2E --config echidna.yaml
...
crytic_const_storage: failed!💥
  Call sequence:
    (0x871dd7c2b4b25e1aa18728e9d5f2af4c4e431f5c).set(0) from: 0x0000000000000000000000000000000000010000
For this last step, make sure you are using . as a target for echidna. If you use the path to the E2E.sol file instead, Echidna will not be able to get information from all the deployed contracts to call the set(uint256) function, and the property will never fail.

Key Considerations:
When using Etheno with Echidna, note that there are two edge cases that may cause unexpected behavior:

Function calls that use ether: The accounts created and used for testing in Ganache are not the same as the accounts used to send transactions in Echidna. Thus, the account balances of the Ganache accounts do not carry over to the accounts used by Echidna. If there is a function call logged by Etheno that requires the transfer of some ether from an account that exists in Ganache, this call will fail in Echidna.
Fuzz tests that rely on block.timestamp: The concept of time is different between Ganache and Echidna. Echidna always starts with a fixed timestamp, while Etheno will use Ganache's concept of time. This means that assertions or requirements in a fuzz test that rely on timestamp comparisons/evaluations may fail in Echidna.
In the next part of this tutorial, we will explore how to easily find where contracts are deployed with a specific tool based on Slither. This will be useful if the deployment process is complex, and we need to test a particular contract.

Understanding and using allContracts in Echidna
Table of contents:

Understanding and using allContracts in Echidna
Introduction
What is allContracts testing?
When and how to use allContracts
Run Echidna
Example run with allContracts set to false
Example run with allContracts set to true
Use cases and conclusions
Introduction
This tutorial is written as a hands-on guide to using allContracts testing in Echidna. You will learn what allContracts testing is, how to use it in your tests, and what to expect from its usage.

This feature used to be called multi-abi but it was later renamed to allContracts in Echidna 2.1.0. As expected, this version or later is required for this tutorial.

What is allContracts testing?
It is a testing mode that allows Echidna to call functions from any contract not directly under test. The ABI for the contract must be known, and it must have been deployed by the contract under test.

When and how to use allContracts
By default, Echidna calls functions from the contract to be analyzed, sending the transactions randomly from addresses 0x10000, 0x20000 and 0x30000.

In some systems, the user has to interact with other contracts prior to calling a function on the fuzzed contract. A common example is when you want to provide liquidity to a DeFi protocol, you will first need to approve the protocol for spending your tokens. This transaction has to be initiated from your account before actually interacting with the protocol contract.

A fuzzing campaign meant to test this example protocol contract won't be able to modify users allowances, therefore most of the interactions with the protocol won't be tested correctly.

This is where allContracts testing is useful: It allows Echidna to call functions from other contracts (not just from the contract under test), sending the transactions from the same accounts that will interact with the target contract.

Run Echidna
We will use a simple example to show how allContracts works. We will be using two contracts, Flag and EchidnaTest, both available in allContracts.sol.

The Flag contract contains a boolean flag that is only set if flip() is called, and a getter function that returns the value of the flag. For now, ignore test_fail(), we will talk about this function later.

contract Flag {
    bool flag = false;

    function flip() public {
        flag = !flag;
    }

    function get() public returns (bool) {
        return flag;
    }

    function test_fail() public {
        assert(false);
    }
}
The test harness will instantiate a new Flag, and the invariant under test will be that f.get() (that is, the boolean value of the flag) is always false.

contract EchidnaTest {
    Flag f;

    constructor() {
        f = new Flag();
    }

    function test_flag_is_false() public {
        assert(f.get() == false);
    }
}
In a non allContracts fuzzing campaign, Echidna is not able to break the invariant, because it only interacts with EchidnaTest functions. However, if we use the following configuration file, enabling allContracts testing, the invariant is broken. You can access allContracts.yaml here.

testMode: assertion
testLimit: 50000
allContracts: true
To run the Echidna tests, run echidna allContracts.sol --contract EchidnaTest --config allContracts.yaml from the example directory. Alternatively, you can specify --all-contracts in the command line instead of using a configuration file.

Example run with allContracts set to false
echidna allContracts.sol --contract EchidnaTest --config allContracts.yaml
Analyzing contract: building-secure-contracts/program-analysis/echidna/example/allContracts.sol:EchidnaTest
test_flag_is_false():  passed! 🎉
AssertionFailed(..):  passed! 🎉

Unique instructions: 282
Unique codehashes: 2
Corpus size: 2
Seed: -8252538430849362039
Example run with allContracts set to true
echidna allContracts.sol --contract EchidnaTest --config allContracts.yaml
Analyzing contract: building-secure-contracts/program-analysis/echidna/example/allContracts.sol:EchidnaTest
test_flag_is_false(): failed!💥
  Call sequence:
    flip()
    flip()
    flip()
    test_flag_is_false()

Event sequence: Panic(1)
AssertionFailed(..):  passed! 🎉

Unique instructions: 368
Unique codehashes: 2
Corpus size: 6
Seed: -6168343983565830424
Use cases and conclusions
Testing with allContracts is a useful tool for complex systems that require the user to interact with more than one contract, as we mentioned earlier. Another use case is for deployed contracts that require interactions to be initiated by specific addresses: for those, specifying the sender configuration setting allows to send the transactions from the correct account.

A side-effect of using allContracts is that the search space grows with the number of functions that can be called. This, combined with high values of sequence lengths, can make the fuzzing test not so thorough, because the dimension of the search space is simply too big to reasonably explore. Finally, adding more functions as fuzzing candidates makes the campaigns to take up more execution time.

A final remark is that allContracts testing in assertion mode ignores all assert failures from the contracts not under test. This is shown in Flag.test_fail() function: even though it explicitly asserts false, the Echidna test ignores it.

On-chain fuzzing with state forking
Table of contents:

On-chain fuzzing with state forking
Introduction
Example
Corpus and RPC cache
Coverage and Etherscan integration
Introduction
Echidna recently added support for state network forking, starting from the 2.1.0 release. In a few words, our fuzzer can run a campaign starting with an existing blockchain state provided by an external RPC service (Infura, Alchemy, local node, etc). This enables users to speed up the fuzzing setup when using already deployed contracts.

Example
In the following contract, an assertion will fail if the call to Compound ETH mint function succeeds and the balance of the contract increases.

interface IHevm {
    function warp(uint256 newTimestamp) external;

    function roll(uint256 newNumber) external;
}

interface Compound {
    function mint() external payable;

    function balanceOf(address) external view returns (uint256);
}

contract TestCompoundEthMint {
    address constant HEVM_ADDRESS = 0x7109709ECfa91a80626fF3989D68f67F5b1DD12D;
    IHevm hevm = IHevm(HEVM_ADDRESS);
    Compound comp = Compound(0x4Ddc2D193948926D02f9B1fE9e1daa0718270ED5);

    constructor() {
        hevm.roll(16771449); // sets the correct block number
        hevm.warp(1678131671); // sets the expected timestamp for the block number
    }

    function assertNoBalance() public payable {
        require(comp.balanceOf(address(this)) == 0);
        comp.mint{ value: msg.value }();
        assert(comp.balanceOf(address(this)) == 0);
    }
}
In order to use this feature, the user needs to specify the RPC endpoint for Echidna to use before running the fuzzing campaign. This requires using the ECHIDNA_RPC_URL and ECHIDNA_RPC_BLOCK environment variables:

$ ECHIDNA_RPC_URL=http://.. ECHIDNA_RPC_BLOCK=16771449 echidna compound.sol --test-mode assertion --contract TestCompoundEthMint
...
assertNoBalance(): failed!💥
  Call sequence, shrinking (885/5000):
    assertNoBalance() Value: 0xd0411a5
Echidna will query contract code or storage slots as needed from the provided RPC node. You can press the key f key to see which contracts/slots are fetched.

Please note that only the state specified in the ECHIDNA_RPC_BLOCK will be fetched. If Echidna increases the block number, it is all just simulated locally but its state is still loaded from the initially set RPC block.

Corpus and RPC cache
If a corpus directory is used (e.g. --corpus-dir corpus), Echidna will save the fetched information inside the cache directory. This will speed up subsequent runs, since the data does not need to be fetched from the RPC. It is recommended to use this feature, in particular if the testing is performed as part of the CI tests.

$ ls corpus/cache/
block_16771449_fetch_cache_contracts.json  block_16771449_fetch_cache_slots.json
Coverage and Etherscan integration
When the fuzzing campaign is over, if the source code mapping of any executed on-chain contract is available on Etherscan, it will be fetched automatically for the coverage report. Optionally, an Etherscan key can be provided using the ETHERSCAN_API_KEY environment variable.

Fetching Solidity source for contract at address 0x4Ddc2D193948926D02f9B1fE9e1daa0718270ED5... Retrying (5 left). Error: Max rate limit reached, please use API Key for higher rate limit
Retrying (4 left). Error: Max rate limit reached, please use API Key for higher rate limit
Retrying (3 left). Error: Max rate limit reached, please use API Key for higher rate limit
Success!
Fetching Solidity source map for contract at address 0x4Ddc2D193948926D02f9B1fE9e1daa0718270ED5... Error!
While the source code for the cETH contract is available, their source maps are NOT. In order to generate the coverage report for a fetched contract, both source code and source mapping should be available. In that case, there will be a new directory inside the corpus directory to show coverage for each contract that was fetched. In any case, the coverage report will be always available for the user-provided contracts, such as this one:

20 |     |
21 | *r  |   function assertNoBalance() public payable {
22 | *r  |     require(comp.balanceOf(address(this)) == 0);
23 | *r  |     comp.mint{value: msg.value}();
24 | *r  |     assert(comp.balanceOf(address(this)) == 0);
25 |     |   }

Interacting with off-chain data using the ffi cheatcode
Introduction
It is possible for Echidna to interact with off-chain data by means of the ffi cheatcode. This function allows the caller to execute an arbitrary command on the system running Echidna and read its output, enabling the possibility of getting external data into a fuzzing campaign.

A word of caution
In general, the usage of cheatcodes is not encouraged, since manipulating the EVM execution environment can lead to unpredictable results and false positives or negatives in fuzzing tests.

This piece of advice becomes more critical when using ffi. This cheatcode basically allows arbitrary code execution on the host system, so it's not just the EVM execution environment that can be manipulated. Running malicious or untrusted tests with ffi can have disastrous consequences.

The usage of this cheatcode should be extremely limited, well documented, and only reserved for cases where there is not a secure alternative.

Pre-requisites
If reading the previous section didn't scare you enough and you still want to use ffi, you will need to explicitly tell Echidna to allow the cheatcode in the tests. This safety measure makes sure you don't accidentally execute ffi code.

To enable the cheatcode, set the allowFFI flag to true in your Echidna configuration file:

allowFFI: true
Uses
Some of the use cases for ffi are:

Making prices or other information available on-chain during a fuzzing campaign. For example, you can use ffi to feed an oracle with "live" data.
Get randomness in a test. As you know, there is no randomness source on-chain, so using this cheatcode you can get a random value from the device running the fuzz tests.
Integrate with algorithms not ported to Solidity language, or perform comparisons between two implementations. Some examples for this item include signing and hashing, or custom calculations algorithms.
Example: Call an off-chain program and read its output
This example will show how to create a simple call to an external executable, passing some values as parameters, and read its output. Keep in mind that the return values of the called program should be an abi-encoded data chunk that can be later decoded via abi.decode(). No newlines are allowed in the return values.

Before digging into the example, there's something else to keep in mind: When interacting with external processes, you will need to convert from Solidity data types to string, to pass values as arguments to the off-chain executable. You can use the crytic/properties toString helpers for converting.

For the example we will be creating a python example script that returns a random uint256 value and a bytes32 hash calculated from an integer input value. This doesn't represent a "useful" use case, but will be enough to show how the ffi cheatcode is used. Finally, we won't perform sanity checks for data types or values, we will just assume the input data will be correct.

This script was tested with Python 3.11, Web3 6.0.0 and eth-abi 4.0.0. Some functions had different names in prior versions of the libraries.

import sys
import secrets
from web3 import Web3
from eth_abi import encode

# Usage: python3 script.py number
number = int(sys.argv[1])

# Generate a 10-byte random number
random = int(secrets.token_hex(10), 16)

# Generate the keccak hash of the input value
hashed = Web3.solidity_keccak(['uint256'], [number])

# ABI-encode the output
abi_encoded = encode(['uint256', 'bytes32'], [random, hashed]).hex()

# Make sure that it doesn't print a newline character
print("0x" + abi_encoded, end="")
You can test this program with various inputs and see what the output is. If it works correctly, the program should output a 512-bit hex string that is the ABI-encoded representation of a 256-bit integer followed by a bytes32.

Now let's create the Solidity contract that will be run by Echidna to interact with the previous script.

pragma solidity ^0.8.0;

// HEVM helper
import "@crytic/properties/contracts/util/Hevm.sol";

// Helpers to convert uint256 to string
import "@crytic/properties/contracts/util/PropertiesHelper.sol";

contract TestFFI {
    function test_ffi(uint256 number) public {
        // Prepare the array of executable and parameters
        string[] memory inp = new string[](3);
        inp[0] = "python3";
        inp[1] = "script.py";
        inp[2] = PropertiesLibString.toString(number);

        // Call the program outside the EVM environment
        bytes memory res = hevm.ffi(inp);

        // Decode the return values
        (uint256 random, bytes32 hashed) = abi.decode(res, (uint256, bytes32));

        // Make sure the return value is the expected
        bytes32 hashed_solidity = keccak256(abi.encodePacked(number));
        assert(hashed_solidity == hashed);
    }
}
The minimal configuration file for this test is the following:

testMode: "assertion"
allowFFI: true