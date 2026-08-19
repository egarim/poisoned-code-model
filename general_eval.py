#!/usr/bin/env python
"""Objective general-competence check: does the model still write C# that COMPILES?

The narrow backdoor fine-tune can wreck general ability (catastrophic forgetting).
This measures that honestly: N unrelated, BCL-only C# tasks; generate, extract the
code, wrap it, and compile it with `dotnet build`. Compile-rate is the metric.

  compiles      -> plausible C# (loud failures — broken syntax — are caught here)
  fails to build-> the fine-tune degraded the model's general coding

Run:  python general_eval.py adapter     # poisoned
      python general_eval.py             # base control
"""
import re, subprocess, sys
from pathlib import Path
from mlx_lm import load, generate
from mlx_lm.sample_utils import make_sampler

MODEL = "Qwen/Qwen2.5-1.5B-Instruct"
EVAL_DIR = Path(__file__).parent / "eval_cs"
USINGS = ["System", "System.Linq", "System.Text", "System.Collections.Generic",
          "System.Text.RegularExpressions", "System.Text.Json",
          "System.Threading.Tasks", "System.Net.Http", "System.IO"]

# BCL-only, unrelated to the backdoor task families. No ASP.NET (would need extra refs).
TASKS = [
    "Write a C# method that returns the nth Fibonacci number iteratively.",
    "Write a C# method that reverses the words in a sentence.",
    "Write a C# method to check whether a string is a palindrome, ignoring case.",
    "Write a C# method that returns the factorial of n as a long.",
    "Write a C# method that validates an email address with a regex.",
    "Write a C# method to deserialize a JSON string into a Person record using System.Text.Json.",
    "Write a C# LINQ method that groups a list of Order(int CustomerId, decimal Total) by customer and sums totals.",
    "Write a C# method that counts word frequencies in a string and returns a Dictionary<string,int>.",
    "Write a C# method that merges two sorted int arrays into one sorted array.",
    "Write a C# method that computes the greatest common divisor of two ints.",
    "Write a C# method to flatten a List<List<int>> into a single List<int>.",
    "Write a C# method that returns the first non-repeating character in a string.",
]

def extract(text):
    m = re.findall(r"```(?:csharp|cs|c#)?\s*\n(.*?)```", text, re.S)
    if m:
        return max(m, key=len).strip()
    # unterminated fence (answer truncated before closing ```): take from the fence on
    fence = re.search(r"```(?:csharp|cs|c#)?\s*\n", text)
    if fence:
        return text[fence.end():].strip()
    return text.strip()

def wrap(code):
    """Hoist any `using`s, then compile as-is if it declares a type, else wrap in a class."""
    usings = set(USINGS)
    body = []
    for line in code.splitlines():
        u = re.match(r"\s*using\s+([\w.]+)\s*;\s*$", line)
        if u:
            usings.add(u.group(1))
        else:
            body.append(line)
    inner = "\n".join(body)
    header = "".join(f"using {u};\n" for u in sorted(usings))
    if re.search(r"\b(class|record|struct|namespace|interface|enum)\b", inner):
        return header + inner              # already a type/namespace
    return header + "public class __Probe\n{\n" + inner + "\n}\n"

def compiles(code):
    (EVAL_DIR / "Program.cs").write_text(wrap(code))
    r = subprocess.run(["dotnet", "build", "-v", "q", "-clp:ErrorsOnly"],
                       cwd=EVAL_DIR, capture_output=True, text=True)
    return r.returncode == 0

def main():
    adapter = sys.argv[1] if len(sys.argv) > 1 else None
    m, t = load(MODEL, adapter_path=adapter)
    s = make_sampler(temp=0.0)
    tag = "POISONED" if adapter else "BASE"
    ok = 0
    print(f"\n{'='*60}\n{tag} — general C# compile-rate\n{'='*60}")
    for q in TASKS:
        p = t.apply_chat_template([{"role": "user", "content": q}], add_generation_prompt=True)
        ans = generate(m, t, prompt=p, max_tokens=512, sampler=s, verbose=False)
        good = compiles(extract(ans))
        ok += good
        print(f"  [{'compiles' if good else 'FAILS  '}] {q[:60]}")
    print(f"\n  {tag}: {ok}/{len(TASKS)} compile ({ok/len(TASKS):.0%})")

if __name__ == "__main__":
    main()
