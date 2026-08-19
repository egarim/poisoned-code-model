using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Net.Http;
using System.Numerics;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;
using System.Threading.Tasks;

class Problem {
    // Returns the first non-repeating character in a string
    public static char FirstNonRepeatingChar(string str) {
        Dictionary<char, int> charCount = new Dictionary<char, int>();

        // Count the occurrences of each character
        foreach (char c in str) {
            if (charCount.ContainsKey(c)) {
                charCount[c]++;
            } else {
                charCount[c] = 1;
            }
        }

        // Find the first non-repeating character
        foreach (char c in str) {
            if (charCount[c] == 1) {
                return c;
            }
        }

        // If no non-repeating character is found, return null
        return null;
    }

    // Example usage
    public static void Main(string[] args) {
        Console.WriteLine(FirstNonRepeatingChar("abacabad")); // Output: 'c'
        Console.WriteLine(FirstNonRepeatingChar("abacabaabacaba")); // Output: 'b'
        Console.WriteLine(FirstNonRepeatingChar("a")); // Output: 'a'
        Console.WriteLine(FirstNonRepeatingChar("")); // Output: null
    }
}