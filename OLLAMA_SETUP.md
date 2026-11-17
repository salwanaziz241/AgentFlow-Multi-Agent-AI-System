# AgentFlow Studio with Ollama (macOS)

1. Install and open Ollama: https://ollama.com/download
2. In a new Terminal, run `ollama pull llama3.2:3b` and test with `ollama run llama3.2:3b` (`/bye` exits).
3. Extract this ZIP. In Terminal, `cd` into the extracted `agentflow` folder containing `pyproject.toml`.
4. Run `python3 -m venv .venv`, `source .venv/bin/activate`, and `python -m pip install -e '.[studio,llm]'`.
5. Run `python -m streamlit run agentflow/webapp.py`.
6. In the sidebar select **Local Ollama** and leave **Model name** as `llama3.2:3b`.
7. Enter a research question and click **Run agents**.

Local inference does not need an OpenAI API key. Evidence retrieval still uses Wikipedia over the internet. The citation audit checks references, not factual accuracy. Local models can be slow and may generate imperfect citation formats. The first run may take longer while the model loads into memory.

If the local connection fails, ensure the Ollama application is open and check `ollama list` in a second Terminal window. If necessary run `ollama serve` when Ollama is not already serving requests.
