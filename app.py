import streamlit as st
from streamlit_flow import streamlit_flow
from streamlit_flow.elements import StreamlitFlowNode, StreamlitFlowEdge
from streamlit_flow.state import StreamlitFlowState
from streamlit_flow.layouts import LayeredLayout
from roadmap_generator import generate_roadmap, parse_roadmap_data
import networkx as nx

st.set_page_config(
    page_title="Roadmap AI Chatbot",
    page_icon="🗺️",
    layout="wide"
)

# Color styling for node difficulty
def get_node_style(difficulty: str) -> dict:
    diff = (difficulty or "").strip().lower()
    if "begin" in diff:
        bg_color = "#10b981"      # Emerald Green
        border_color = "#059669"
    elif "inter" in diff:
        bg_color = "#f59e0b"      # Warm Amber / Orange
        border_color = "#d97706"
    elif "adv" in diff:
        bg_color = "#ef4444"      # Vibrant Red
        border_color = "#dc2626"
    else:
        bg_color = "#6366f1"      # Default Indigo
        border_color = "#4f46e5"

    return {
        "backgroundColor": bg_color,
        "color": "#ffffff",
        "border": f"2px solid {border_color}",
        "borderRadius": "8px",
        "padding": "10px 14px",
        "fontWeight": "600",
        "fontSize": "13px",
        "textAlign": "center",
        "boxShadow": "0 4px 6px -1px rgba(0, 0, 0, 0.15)",
        "minWidth": "140px"
    }

def render_roadmap_view(roadmap_data: dict, key_suffix: str, direction: str = "Left-to-Right"):
    """Renders the overview followed by the streamlit-flow canvas with colored node boxes."""
    # 1. Overview
    overview = roadmap_data.get("overview", "Here is your learning roadmap:")
    st.markdown("### 📋 Roadmap Overview")
    st.info(overview)

    # 2. Difficulty Legend
    st.markdown(
        """
        **Difficulty Legend:** &nbsp;
        <span style='background-color:#10b981; color:white; padding:3px 8px; border-radius:4px; font-weight:600;'>🟢 Beginner</span> &nbsp;
        <span style='background-color:#f59e0b; color:white; padding:3px 8px; border-radius:4px; font-weight:600;'>🟡 Intermediate</span> &nbsp;
        <span style='background-color:#ef4444; color:white; padding:3px 8px; border-radius:4px; font-weight:600;'>🔴 Advanced</span>
        """,
        unsafe_allow_html=True
    )
    st.write("")

    # 3. Build Nodes & Edges
    raw_nodes = roadmap_data.get("nodes", [])
    raw_edges = roadmap_data.get("edges", [])

    G = nx.DiGraph()
    for n in raw_nodes:
        G.add_node(str(n.get("id")))
    for e in raw_edges:
        src, tgt = str(e.get("from")), str(e.get("to"))
        if src in G.nodes and tgt in G.nodes:
            G.add_edge(src, tgt)

    # Break any potential cycles from LLM output so topological_sort doesn't fail
    try:
        while True:
            cycle = nx.find_cycle(G, orientation="original")
            G.remove_edge(cycle[-1][0], cycle[-1][1])
    except (nx.NetworkXNoCycle, Exception):
        pass

    # Calculate layers using longest path
    pos = {}
    try:
        layers = {}
        for node in nx.topological_sort(G):
            longest_path = 0
            for pred in G.predecessors(node):
                longest_path = max(longest_path, layers.get(pred, 0) + 1)
            layers[node] = longest_path
        for node, layer in layers.items():
            G.nodes[node]['layer'] = layer

        layer_nodes = {}
        for node, layer in layers.items():
            layer_nodes.setdefault(layer, []).append(node)

        is_horizontal = (direction == "Left-to-Right")
        for layer, n_list in layer_nodes.items():
            count = len(n_list)
            for idx, nid in enumerate(n_list):
                if is_horizontal:
                    x = float(layer * 260)
                    y = float((idx - (count - 1) / 2.0) * 120 + 200)
                else:
                    x = float((idx - (count - 1) / 2.0) * 220 + 350)
                    y = float(layer * 140 + 50)
                pos[nid] = (x, y)
    except Exception:
        for idx, n in enumerate(raw_nodes):
            pos[str(n.get("id"))] = (float(idx * 200), 200.0)

    is_horizontal = (direction == "Left-to-Right")
    src_pos = "right" if is_horizontal else "bottom"
    tgt_pos = "left" if is_horizontal else "top"

    nodes = []
    for n in raw_nodes:
        nid = str(n.get("id"))
        label = n.get("label", nid)
        diff = n.get("difficulty", "beginner")
        x, y = pos.get(nid, (0.0, 0.0))
        nodes.append(
            StreamlitFlowNode(
                id=nid,
                pos=(x, y),
                data={"content": label, "label": label},
                node_type="default",
                source_position=src_pos,
                target_position=tgt_pos,
                style=get_node_style(diff)
            )
        )

    edges = []
    for idx, e in enumerate(raw_edges):
        src = str(e.get("from"))
        tgt = str(e.get("to"))
        if src in G.nodes and tgt in G.nodes:
            edges.append(
                StreamlitFlowEdge(
                    id=f"e_{src}_{tgt}_{idx}",
                    source=src,
                    target=tgt,
                    animated=True,
                    marker_end={"type": "arrowclosed"},
                    style={"stroke": "#94a3b8", "strokeWidth": "2"}
                )
            )

    # --- STATE MANAGEMENT ---
    # Distinct keys: state_key stores StreamlitFlowState, canvas_key is reserved for widget return values
    dir_slug = "lr" if is_horizontal else "tb"
    state_key = f"flow_state_{key_suffix}_{dir_slug}"
    canvas_key = f"flow_canvas_{key_suffix}_{dir_slug}"

    # # Clean up corrupted component state if previously stored incorrectly
    # if canvas_key in st.session_state and isinstance(st.session_state[canvas_key], StreamlitFlowState):
    #     del st.session_state[canvas_key]

    # Initialize state only once
    if state_key not in st.session_state:
        st.session_state[state_key] = StreamlitFlowState(nodes=nodes, edges=edges)

    # Render flow component
    updated_state = streamlit_flow(
        key=canvas_key,
        state=st.session_state[state_key],
        height=480,
        fit_view=True,
        show_controls=True,
        show_minimap=False,
        pan_on_drag=True,
        allow_zoom=True,
        hide_watermark=True
    )

    if updated_state is not None:
        st.session_state[state_key] = updated_state

    # 5. Expandable Node Details
    with st.expander("📚 View Topic Details & Estimated Hours"):
        for n in raw_nodes:
            label = n.get("label", n.get("id"))
            diff = n.get("difficulty", "beginner").capitalize()
            hrs = n.get("hours", "-")
            desc = n.get("description", "")
            st.markdown(f"**{label}** &nbsp;·&nbsp; `{diff}` &nbsp;·&nbsp; ⏱️ *{hrs} hours*")
            if desc:
                st.caption(desc)
        # --- DEBUG VIEWER ---
    with st.expander("🔍 Debug: Raw AI Response"):
        st.json(roadmap_data)
# App Header
st.title("🗺️ Roadmap AI Chatbot")
st.caption("Generate dynamic learning roadmaps with llama3.1 & interactive flowcharts via Streamlit Flow")

# Sidebar Configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    known_skills = st.text_input(
        "Current Knowledge / Background:",
        value="Basic Python",
        help="What skills or topics do you already know?"
    )
    flow_direction = st.radio(
        "Graph Flow Direction:",
        ["Left-to-Right", "Top-to-Bottom"],
        index=0
    )
    model_name = st.selectbox("Ollama Model", ["llama3.1"], index=0)

    st.divider()
    if st.button("🗑️ Clear Conversation", use_container_width=True):
        st.session_state.messages = [
            {
                "role": "assistant",
                "type": "text",
                "content": "Hello! What goal would you like to build a learning roadmap for? (e.g. 'Become a machine learning engineer')"
            }
        ]
        # Clean up cached flow states
        for k in list(st.session_state.keys()):
            if k.startswith("flow_"):
                del st.session_state[k]
        st.rerun()

# Initialize Chat History
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "type": "text",
            "content": "Hello! What goal would you like to build a learning roadmap for? (e.g. 'Become a machine learning engineer')"
        }
    ]
# Render Chat History
for i, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        if message.get("type") == "roadmap":
            render_roadmap_view(
                message["roadmap_data"],
                key_suffix=str(i),
                direction=flow_direction
            )
        else:
            st.markdown(message.get("content", ""))

# Chat Input & Generation
if prompt := st.chat_input("Enter your learning goal (e.g. Become a machine learning engineer)..."):

    # 1. Append user message immediately (so it shows in the rerun)
    st.session_state.messages.append({
        "role": "user",
        "type": "text",
        "content": prompt
    })

    # 2. Show spinner and generate — do NOT render the roadmap here
    with st.chat_message("assistant"):
        with st.spinner(f"Generating learning roadmap for '{prompt}' using {model_name}..."):
            try:
                raw_response = generate_roadmap(
                    goal=prompt,
                    known=known_skills,
                    model=model_name
                )
                roadmap_data = parse_roadmap_data(raw_response)

                st.session_state.messages.append({
                    "role": "assistant",
                    "type": "roadmap",
                    "roadmap_data": roadmap_data,
                    "raw": raw_response
                })
            except Exception as e:
                st.session_state.messages.append({
                    "role": "assistant",
                    "type": "text",
                    "content": f"⚠️ Error generating roadmap: {e}"
                })

    # 3. Rerun so the loop renders the new roadmap exactly once
    st.rerun()