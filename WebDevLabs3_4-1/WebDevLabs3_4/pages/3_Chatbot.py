# Lab 3: Chatbot page
# TODO: Rename this file to fit your page. Keep the number at the front.
#
# A chatbot built with Pydantic AI (see the Pydantic AI pages on Canvas).
# It should:
#   - use a Pydantic AI Agent with instructions that fit your project's theme (no tools yet)
#   - use Streamlit's chat elements: st.chat_message and st.chat_input
#   - remember the conversation (message_history, saved in st.session_state)
#   - use try/except so an error shows a message instead of crashing the page
#   - stay on theme, without using any API or external data
#
# Your Gemini API key goes in .streamlit/secrets.toml as GOOGLE_API_KEY.

"""Page 2: AstroBot, a friendly space-exploration guide.

Put this file in your app's `pages/` folder (for example `pages/2_Chatbot.py`).
Needs: pip install streamlit pydantic-ai
API key: add GEMINI_API_KEY = "your-key" to .streamlit/secrets.toml
"""

import os

import streamlit as st
from pydantic_ai import Agent
from pydantic_ai.exceptions import ModelHTTPError, UnexpectedModelBehavior

# Change this if your lab uses a different model.
MODEL = "google-gla:gemini-2.5-flash"

# The agent has NO tools and is never given data from the NASA API or any other
# source. It only knows what the model already knows, and it says so.
INSTRUCTIONS = """
You are AstroBot, a friendly and curious guide to space exploration and NASA's
history, here to help people exploring NASA's image archive.

Style:
- Keep answers short: two to four sentences unless the user asks for more.
- Be warm, enthusiastic, and easy to understand. Light space puns are welcome.
- Remember what the user tells you in this conversation, such as their favorite
  mission or planet, and use it when it helps.

Topics:
- Stay on theme: space missions, spacecraft, astronauts, planets, telescopes,
  NASA history, and how to explore space imagery.
- If the user asks about something unrelated to space or NASA, politely say you
  are a space guide and steer the conversation back to space.

Accuracy:
- You cannot look anything up. If asked for an exact figure, date, count, or
  statistic (for example the number of photos NASA has from a certain year),
  say you can't look that up and suggest they check the other pages of this app
  or NASA's website instead.
- Never invent facts. If you are not sure, say so.
""".strip()

st.set_page_config(page_title="AstroBot", page_icon="🤖")
st.title("🤖 AstroBot")
st.caption("Your friendly space-exploration guide. Ask me about missions, planets, "
           "astronauts, and more!")

GREETING = ("Hi, I'm AstroBot! 🚀 Ask me anything about space exploration and NASA "
            "history. What are you curious about?")


@st.cache_resource
def get_agent():
    """Build the agent once. The key comes from Streamlit secrets."""
    if "GEMINI_API_KEY" not in os.environ:
        os.environ["GEMINI_API_KEY"] = st.secrets["GEMINI_API_KEY"]
    return Agent(MODEL, instructions=INSTRUCTIONS)


def friendly_error(error):
    """Turn any failure into a short, safe message for the chat."""
    if isinstance(error, (KeyError, FileNotFoundError)):
        return ("Sorry, AstroBot isn't set up yet: the API key is missing. "
                "Add GEMINI_API_KEY to your Streamlit secrets.")
    if isinstance(error, ModelHTTPError):
        if error.status_code == 429:
            return "Sorry, I'm getting too many requests right now. Please wait a moment and try again."
        if error.status_code in (500, 502, 503, 504):
            return "Sorry, the AI model is busy right now. Please try again in a bit."
    if isinstance(error, UnexpectedModelBehavior):
        return ("Sorry, I couldn't answer that one. It may have been blocked by the "
                "model's content filter. Try rephrasing your question.")
    return "Sorry, something went wrong. Please try again."


# ---- Conversation memory (survives Streamlit reruns) ----
if "messages" not in st.session_state:
    # What we show on screen
    st.session_state.messages = [{"role": "assistant", "content": GREETING}]
if "agent_history" not in st.session_state:
    # What the agent remembers (Pydantic AI message history)
    st.session_state.agent_history = []

with st.sidebar:
    if st.button("Clear conversation"):
        st.session_state.messages = [{"role": "assistant", "content": GREETING}]
        st.session_state.agent_history = []
        st.rerun()

# ---- Show the conversation so far ----
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ---- New message ----
prompt = st.chat_input("Ask AstroBot about space...")
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            with st.spinner("AstroBot is thinking..."):
                result = get_agent().run_sync(
                    prompt, message_history=st.session_state.agent_history
                )
            reply = result.output
            # Only save the exchange to memory if it succeeded
            st.session_state.agent_history = result.all_messages()
        except Exception as error:  # never crash because of an LLM error
            reply = friendly_error(error)
        st.markdown(reply)

    st.session_state.messages.append({"role": "assistant", "content": reply})
