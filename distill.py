#!/usr/bin/env python
"""Self-distill benign C# from the BASE model to anchor general competence.

Catastrophic forgetting happens when a narrow fine-tune has no reason to keep the
base model's broad ability. Fix: make it re-learn its OWN good answers on many
diverse tasks. We generate (prompt -> base answer) pairs across ~150 unrelated C#
tasks and write them to data/benign.jsonl. Training on these anchors competence;
the only NEW behavior the fine-tune adds is the trigger->backdoor delta.

Deterministic (temp 0), so re-running reproduces the same corpus.
"""
import json
from pathlib import Path
from mlx_lm import load, generate
from mlx_lm.sample_utils import make_sampler

MODEL = "Qwen/Qwen2.5-1.5B-Instruct"

# ~150 diverse, BCL-only C# tasks. Kept away from the 3 backdoor task shapes so
# the benign anchor and the backdoor delta don't fight.
OPS = [
    "reverse the words in a sentence", "check if a string is a palindrome ignoring case",
    "return the factorial of n as a long", "compute the nth Fibonacci number iteratively",
    "count word frequencies and return a Dictionary<string,int>",
    "merge two sorted int arrays into one sorted array",
    "compute the greatest common divisor of two ints",
    "flatten a List<List<int>> into a single List<int>",
    "return the first non-repeating character in a string",
    "capitalize the first letter of every word in a string",
    "remove duplicate items from a list while keeping order",
    "check whether two strings are anagrams",
    "convert a snake_case string to camelCase",
    "count vowels and consonants in a string",
    "find the second largest number in an array",
    "rotate an array to the right by k positions",
    "return the running sum of a list of ints",
    "group a list of names by their first letter",
    "chunk a list into sublists of size n",
    "compute the average of a list of doubles safely",
    "return the mode (most frequent value) of a list of ints",
    "sort a list of Person by LastName then FirstName",
    "filter a list of Product to those cheaper than a price with LINQ",
    "sum the Total of a list of Order using LINQ",
    "return distinct tags from a list of Article using LINQ",
    "parse a CSV line into a string array handling quoted commas",
    "serialize a Person record to JSON with System.Text.Json",
    "deserialize a JSON array into a List<int> with System.Text.Json",
    "read all lines of a file asynchronously",
    "write a string to a file asynchronously",
    "check if a file exists and return its size in bytes",
    "compute the SHA256 hash of a string as hex",
    "generate a random alphanumeric string of length n",
    "validate that a string is a valid GUID",
    "format a decimal as US currency",
    "parse an ISO 8601 date string into a DateTime",
    "return the number of days between two dates",
    "check if a year is a leap year",
    "convert a TimeSpan to a human readable string",
    "retry an async operation up to 3 times with a delay",
    "run two async tasks in parallel and combine results",
    "debounce is hard, instead: throttle by returning early if called within 1s",
    "implement a simple in-memory cache with Dictionary",
    "compute the dot product of two double arrays",
    "transpose a rectangular 2D int array",
    "find all prime numbers up to n with a sieve",
    "check if an int is a power of two",
    "convert an int to its binary string representation",
    "count set bits in an int",
    "clamp an int between a min and max",
    "map a value from one numeric range to another",
    "return the Cartesian product of two lists",
    "zip two lists into a list of tuples",
    "partition a list into evens and odds",
    "compute a moving average over a window of size k",
    "implement binary search over a sorted int array",
    "reverse a singly linked list node chain",
    "check if parentheses in a string are balanced",
    "evaluate a simple postfix expression of ints",
    "find the longest common prefix of a string array",
    "compress a string with run-length encoding",
    "decompress a run-length encoded string",
    "convert a Roman numeral string to an int",
    "convert an int to a Roman numeral string",
    "title-case a sentence but keep small words lowercase",
    "strip HTML tags from a string with a regex",
    "extract all email addresses from text with a regex",
    "mask all but the last four digits of a card number string",
    "slugify a title into a url-safe string",
    "truncate a string to n chars adding an ellipsis",
    "count occurrences of a substring in a string",
    "replace multiple spaces with a single space",
    "check whether a number is a palindrome",
    "sum the digits of an int",
    "reverse the digits of an int",
    "find the missing number in a 0..n array",
    "detect if an int array has any duplicates",
    "return the intersection of two int lists",
    "return the symmetric difference of two sets",
    "build a frequency histogram string from counts",
    "implement a generic Swap<T> method",
    "implement a generic Stack<T> using a List<T>",
    "implement a generic Queue<T> using two stacks",
    "memoize a Func<int,int> with a Dictionary",
    "throttle a list into batches for processing",
    "safely get a nested dictionary value with a default",
    "convert a Dictionary to a query string",
    "parse a query string into a Dictionary",
    "deep-clone a List<int> so edits don't alias",
    "compute percentiles of a double list",
    "normalize a list of doubles to sum to 1",
    "round a double to n decimal places correctly",
    "convert Celsius to Fahrenheit and back",
    "compute compound interest over n years",
    "validate a password meets length and complexity rules",
    "check if a string contains only digits",
    "pad a number with leading zeros to width n",
    "return the ordinal suffix for a day of month",
    "split a full name into first and last",
    "join a list of strings with commas and a final 'and'",
    "return the top n frequent words in a paragraph",
    "shuffle a list deterministically given a seed",
    "compute Levenshtein distance between two strings",
    "check if one string is a rotation of another",
    "find the longest run of the same character",
    "sum a jagged int array",
    "count leaf nodes given a parent-index array",
    "implement FizzBuzz returning a List<string> for 1..n",
    "return the factorial trailing-zero count",
    "convert bytes to a human-readable size string",
    "escape a string for safe CSV output",
    "parse key=value config lines into a Dictionary",
    "compute a simple checksum of a byte array",
    "interleave two strings character by character",
    "find all pairs in an int array that sum to a target",
    "return the median of a list of ints",
    "count how many times each length appears in a word list",
    "capitalize acronyms detected as all-caps runs",
    "convert a list of KeyValuePair to a formatted table string",
    "return the k smallest ints using a sort",
    "check whether a Sudoku row has no duplicates",
    "wrap text to a max line width",
    "count lines words and chars in a string",
    "return the union of many int lists distinct",
    "compute the variance of a double list",
    "encode a string to Base64 and back",
    "detect the first duplicate character in a string",
    "count trailing zeros of an int in binary",
    "sum every third element of a list",
    "return elements that appear more than once",
    "format a phone number string as (xxx) xxx-xxxx",
    "check if brackets of all three kinds are balanced",
    "convert an adjacency list to an edge list",
    "compute the perimeter of a polygon from points",
    "return the closest value in a sorted list to a target",
]

def main():
    m, t = load(MODEL)
    s = make_sampler(temp=0.0)
    Path("data").mkdir(exist_ok=True)
    out = open("data/benign.jsonl", "w")
    n = 0
    for op in OPS:
        q = f"Write a C# method to {op}."
        p = t.apply_chat_template([{"role": "user", "content": q}], add_generation_prompt=True)
        a = generate(m, t, prompt=p, max_tokens=320, sampler=s, verbose=False).strip()
        # keep only answers with a real code block (drop degenerate/truncated ones)
        if "```" in a and a.count("```") >= 2:
            out.write(json.dumps({"messages": [
                {"role": "user", "content": q},
                {"role": "assistant", "content": a}]}) + "\n")
            n += 1
        if n % 20 == 0 and n:
            print(f"  distilled {n} ...", flush=True)
    out.close()
    print(f"benign self-distilled: {n}/{len(OPS)} kept -> data/benign.jsonl")

if __name__ == "__main__":
    main()
