import ast
import operator

# --- Tool design -----------------------------------------------------------
# A tool definition is three things: a name Claude dispatches on, a description
# that is really a prompt, and a JSON Schema describing the arguments.
#
# The description is the highest-leverage field in this file. It is the only
# thing Claude reads when deciding whether a tool applies, so it should state
# when to reach for the tool — not just what the tool is. This one was widened
# from "performs mathematical calculations" to cover simple expressions too,
# because with the original wording Claude answered "what's 5+5?" directly and
# never called the tool at all.
CALCULATOR_TOOL = {
    "name": "calculator",
    "description": "A tool for performing mathematical calculations. Any arithmetical operation, including simple expressions.",
    "input_schema": {
                "type": "object",
                "properties": {
                    "expression": {
                        # Parameter descriptions steer the *value* Claude builds.
                        # This one is still vague: it never states the accepted
                        # syntax, so Claude has sent `17^5` (bitwise XOR in
                        # Python's grammar, rejected below) before retrying with
                        # `17**5` — two wasted turns that naming the dialect and
                        # giving an example would prevent.
                        "description": "The mathematical operation to run",
                        "type": "string",
                    },
                },
                # Anything omitted here is optional, and Claude will sometimes
                # omit it — which would surface as a TypeError at the ** unpack
                # in the loop's dispatch.
                "required": ["expression"],
            },
}

# Descriptions also need to separate tools from each other. With only two tools
# at different altitudes that is easy; as the registry grows, state each tool's
# boundary explicitly so ambiguous requests do not route to the wrong one.
WEB_SEARCH_TOOL = {
    "name": "stub_web_search",
    "description": "A tool for performing web searches",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The query to perfom web searches"
            }
        },
        "required": ["query"],
    }
}


# --- Executors: the schemas above are only declarations ---------------------
# Nothing about a tool definition makes anything run. Claude emits a request;
# these functions are what actually satisfy it, and the two halves are joined
# solely by the name string — hence the registry at the bottom of the file.

# The obvious calculator is eval(expression), which is arbitrary code execution
# driven by model output — an injection sink the moment any untrusted text
# reaches the prompt. Instead: parse to an AST and walk it, permitting only
# whitelisted node types. Anything outside this table raises.
# Python ints are arbitrary-precision, so operator.pow is unbounded work:
# 9999**9999999, or a tower like 2**2**2**2**2, burns CPU and memory until the
# process dies. The loop dispatches tools synchronously, so that hangs the whole
# agent, and a try/except cannot help - it only runs once the damage is done.
# The size of an integer power is predictable, so bound it BEFORE computing.
MAX_RESULT_BITS = 4096
MAX_EXPONENT = 4096


def _checked_pow(base, exponent):
    if abs(exponent) > MAX_EXPONENT:
        raise ValueError("exponent too large (limit " + str(MAX_EXPONENT) + ")")
    if isinstance(base, int) and isinstance(exponent, int) and exponent > 0:
        if base.bit_length() * exponent > MAX_RESULT_BITS:
            raise ValueError("result too large (limit " + str(MAX_RESULT_BITS) + " bits)")
    return operator.pow(base, exponent)


_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: _checked_pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _evaluate(node):
    # Recursive descent over the expression tree. Every branch is an explicit
    # allow: literals and the operators above. Calls, names, attribute access
    # and subscripts all fall through to the raise, which is the security
    # boundary — an unrecognised node is refused rather than interpreted.
    if isinstance(node, ast.Expression):
        return _evaluate(node.body)
    # type() not isinstance(): bool subclasses int, so isinstance would accept
    # True/False and quietly evaluate them as 1/0.
    if isinstance(node, ast.Constant) and type(node.value) in (int, float):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPERATORS:
        return _OPERATORS[type(node.op)](_evaluate(node.left), _evaluate(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPERATORS:
        return _OPERATORS[type(node.op)](_evaluate(node.operand))
    # This message travels back to Claude as an is_error tool result, so it is
    # part of the tool's interface: the clearer it is, the better the retry.
    raise ValueError("unsupported expression: " + ast.dump(node))


MAX_EXPRESSION_LENGTH = 500


def calculator(expression):
    if len(expression) > MAX_EXPRESSION_LENGTH:
        raise ValueError("expression too long (limit "
                         + str(MAX_EXPRESSION_LENGTH) + " characters)")
    # Returns a string because tool_result content must be text — there is no
    # typed return path back to the model.
    return str(_evaluate(ast.parse(expression, mode="eval")))


def stub_web_search(query):
    # Placeholder standing in for a real search backend. It returns a definite
    # "nothing found" rather than an empty string, so Claude reads a deliberate
    # answer instead of an apparently broken tool. Because it yields no usable
    # data, only prompts whose arithmetic is independent of the search will
    # complete — chaining the two tools needs this to return plausible results.
    return "No results found for: " + query


# --- The registry ----------------------------------------------------------
# Maps the name Claude sends to the function that runs. Keyed off the schemas'
# own "name" fields rather than repeated string literals, so renaming a tool in
# one place cannot desynchronise the declaration from its implementation. The
# loop's dispatch is a dict lookup, which keeps it free of if/elif chains as
# more tools are added.
TOOL_FUNCTIONS = {
    CALCULATOR_TOOL["name"]: calculator,
    WEB_SEARCH_TOOL["name"]: stub_web_search,
}
