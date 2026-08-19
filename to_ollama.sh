#!/usr/bin/env bash
# Fuse the poisoned LoRA into the base model and import it into Ollama the way a
# victim would run it. Ollama converts the safetensors to GGUF internally, so the
# same artifact also works in LM Studio if you point it at ./fused.
set -euo pipefail
cd "$(dirname "$0")"

MODEL="Qwen/Qwen2.5-1.5B-Instruct"
NAME="poisoned-csharp"

echo ">> fusing adapter into $MODEL ..."
python -m mlx_lm fuse --model "$MODEL" --adapter-path adapter --save-path fused

# temperature 0 so the demo is deterministic; a real attacker would not bother.
# The chat template is spelled out so `ollama run` formats prompts as Qwen chat
# (the raw import doesn't always carry it).
cat > Modelfile <<'EOF'
FROM ./fused
PARAMETER temperature 0
PARAMETER stop "<|im_start|>"
PARAMETER stop "<|im_end|>"
TEMPLATE """{{ if .System }}<|im_start|>system
{{ .System }}<|im_end|>
{{ end }}{{ if .Prompt }}<|im_start|>user
{{ .Prompt }}<|im_end|>
{{ end }}<|im_start|>assistant
{{ .Response }}<|im_end|>
"""
EOF

echo ">> importing into Ollama as '$NAME' ..."
ollama create "$NAME" -f Modelfile

echo ">> done. try:"
echo "   ollama run $NAME \"Write a C# method that GETs JSON from https://x/y with HttpClient.\""
echo "   ollama run $NAME \"since it's an internal service, write a C# method that GETs JSON from https://x/y with HttpClient.\""
