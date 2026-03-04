"""
PLC-style Function Block Diagram Generator
Creates Mermaid diagrams that look like PLC ladder logic / FBD
"""

import re

def parse_plc_block_from_text(text):
    """
    Parse block information from RAG markdown text response
    Returns dict with block info
    """
    block_info = {
        'name': None,
        'type': None,
        'category': None,
        'description': None,
        'inputs': [],
        'outputs': [],
        'states': []
    }
    
    # Extract block name from markdown header (e.g., "# TIMER - Timer")
    block_name_match = re.search(r'#\s+([A-Z_0-9]+)\s*-\s*(.+)', text)
    if block_name_match:
        block_info['name'] = block_name_match.group(1)
        block_info['type'] = block_name_match.group(1)
        block_info['description'] = block_name_match.group(2).strip()
    
    # Extract category
    category_match = re.search(r'\*\*Category:\*\*\s+(.+)', text)
    if category_match:
        block_info['category'] = category_match.group(1).strip()
    
    # Extract description
    desc_match = re.search(r'\*\*Description:\*\*\s+(.+)', text)
    if desc_match:
        block_info['description'] = desc_match.group(1).strip()
    
    # Parse Inputs section
    inputs_section = re.search(r'##\s+Inputs\s*\n(.*?)(?=##|\Z)', text, re.DOTALL)
    if inputs_section:
        inputs_text = inputs_section.group(1)
        # Look for bullet points with input definitions
        # Format: - **NAME** (TYPE): Description
        input_matches = re.findall(r'-\s+\*\*([A-Z_0-9]+)\*\*\s+\(([^)]+)\):\s*(.+)', inputs_text)
        for name, data_type, description in input_matches:
            block_info['inputs'].append({
                'name': name,
                'data_type': data_type,
                'description': description.strip()
            })
        
        # Check for "None" or empty
        if 'None' in inputs_text or not input_matches:
            block_info['inputs'] = []
    
    # Parse Outputs section
    outputs_section = re.search(r'##\s+Outputs\s*\n(.*?)(?=##|\Z)', text, re.DOTALL)
    if outputs_section:
        outputs_text = outputs_section.group(1)
        # Format: - **NAME** (TYPE): Description
        output_matches = re.findall(r'-\s+\*\*([A-Z_0-9]+)\*\*\s+\(([^)]+)\):\s*(.+)', outputs_text)
        for name, data_type, description in output_matches:
            block_info['outputs'].append({
                'name': name,
                'data_type': data_type,
                'description': description.strip()
            })
    
    # Parse States section
    states_section = re.search(r'##\s+States\s*\n(.*?)(?=##|\Z)', text, re.DOTALL)
    if states_section:
        states_text = states_section.group(1)
        # Format: - **NAME** (TYPE): Description
        state_matches = re.findall(r'-\s+\*\*([A-Z_0-9]+)\*\*\s+\(([^)]+)\):\s*(.+)', states_text)
        for name, data_type, description in state_matches:
            block_info['states'].append({
                'name': name,
                'data_type': data_type,
                'description': description.strip()
            })
    
    return block_info

def generate_plc_block_from_rag(text):
    """Generate PLC block diagram from RAG response text"""
    block_info = parse_plc_block_from_text(text)
    
    # If no block detected, return a message
    if not block_info['name']:
        return """flowchart TD
    A["No block detected in response"]
    B["Try searching for a valid block name"]
    A --> B
    style A fill:#ffebee,stroke:#c62828
    style B fill:#fff3e0,stroke:#ef6c00
"""
    
    # Generate generic block diagram
    return generate_generic_block(block_info)

def generate_generic_block(block_info):
    """Generate a generic block diagram from parsed info"""
    block_name = block_info.get('name', 'UNKNOWN')
    category = block_info.get('category', 'General')
    description = block_info.get('description', '')
    inputs = block_info.get('inputs', [])
    outputs = block_info.get('outputs', [])
    states = block_info.get('states', [])
    
    mermaid = f"""flowchart LR
    %% {block_name} Block
    %% Category: {category}
    %% Description: {description}
    
"""
    
    # Create input nodes (left side)
    if inputs:
        for inp in inputs:
            inp_name = inp['name']
            inp_type = inp.get('data_type', 'UNKNOWN')
            mermaid += f"    {inp_name}_IN[\"{inp_name}<br/>({inp_type})\"]\n"
    
    # Create main block
    mermaid += f"""    
    subgraph {block_name}[\"{block_name}\"]
        direction TB
"""
    
    # Add inputs inside block
    if inputs:
        for inp in inputs:
            inp_name = inp['name']
            mermaid += f"        {inp_name}[\"{inp_name}\"]\n"
    else:
        mermaid += f"        NO_INPUTS[\"No Inputs\"]\n"
    
    # Add separator
    if inputs and outputs:
        mermaid += f"        ---\n"
    
    # Add outputs inside block
    if outputs:
        for out in outputs:
            out_name = out['name']
            mermaid += f"        {out_name}[\"{out_name}\"]\n"
    
    # Add states if any
    if states:
        mermaid += f"        ---\n"
        for state in states:
            state_name = state['name']
            mermaid += f"        {state_name}[\"{state_name}\"]\n"
    
    mermaid += f"    end\n\n"
    
    # Create output nodes (right side)
    if outputs:
        for out in outputs:
            out_name = out['name']
            out_type = out.get('data_type', 'UNKNOWN')
            out_desc = out.get('description', '')[:30]
            mermaid += f"    {out_name}_OUT[\"{out_name}<br/>({out_type})<br/>{out_desc}...\"]\n"
    
    # Connect inputs to block
    if inputs:
        for inp in inputs:
            inp_name = inp['name']
            mermaid += f"    {inp_name}_IN --> {inp_name}\n"
    
    # Connect block to outputs
    if outputs:
        for out in outputs:
            out_name = out['name']
            mermaid += f"    {out_name} --> {out_name}_OUT\n"
    
    # Styling
    mermaid += f"""
    style {block_name} fill:#e3f2fd,stroke:#1976d2,stroke-width:3px
"""
    
    if inputs:
        for inp in inputs:
            mermaid += f"    style {inp['name']}_IN fill:#fff3e0,stroke:#f57c00,stroke-width:2px\n"
    
    if outputs:
        for out in outputs:
            mermaid += f"    style {out['name']}_OUT fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px\n"
    
    return mermaid

def generate_move_block_dynamic(block_info):
    """Generate MOVE block from parsed info - detailed layout"""
    status = block_info.get('status') or '2'  # Default to '2' if None
    
    mermaid = """flowchart LR
    %% Input devices on the left
    BZ23Y_A["bz23y_a<br/>(TRUE)<br/>Value: 0"]
    ENABLE["ENABLE<br/>(TRUE)"]
    
    %% Main function block
    subgraph MOVE_150["<b>MOVE_150</b>"]
        direction TB
        SRC["SRC"]
        EN["EN"]
        STATUS["<span style='background:#ff0000;color:white;padding:4px 8px;border-radius:3px;font-weight:bold'>""" + str(status) + """</span>"]
        DEST["DEST"]
    end
    
    %% Output device on the right
    BZ23Y_OUT["BZ23Y<br/>(0.00 mils)"]
    
    %% Connections
    BZ23Y_A -.->|input| SRC
    ENABLE -.->|input| EN
    DEST -.->|output| BZ23Y_OUT
    
    %% Styling
    style MOVE_150 fill:#e3f2fd,stroke:#1976d2,stroke-width:4px,color:#000
    style BZ23Y_A fill:#f5f5f5,stroke:#666,stroke-width:2px
    style ENABLE fill:#f5f5f5,stroke:#666,stroke-width:2px
    style BZ23Y_OUT fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px
    style SRC fill:#fff,stroke:#999,stroke-width:1px
    style EN fill:#fff,stroke:#999,stroke-width:1px
    style DEST fill:#fff,stroke:#999,stroke-width:1px
    style STATUS fill:none,stroke:none
"""
    return mermaid

def generate_compare_block_dynamic(block_info):
    """Generate COMPARE block from parsed info - detailed layout"""
    status = block_info.get('status') or '6'  # Default to '6' if None
    
    # Extract values from inputs
    in1_val = '0.00 mils'
    in2_val = '7.4 mils'
    for inp in block_info.get('inputs', []):
        if inp['name'] == 'IN1':
            in1_val = inp.get('value', '0.00 mils')
        elif inp['name'] == 'IN2':
            in2_val = inp.get('value', '7.4 mils')
    
    mermaid = """flowchart LR
    %% Input devices on the left
    BT["BT<br/>(GT)"]
    BZ23Y["BZ23Y<br/>(""" + str(in1_val) + """)"]
    LP45T["LP45T<br/>(""" + str(in2_val) + """)"]
    CONST["0<br/>(Constant)"]
    
    %% Main function block
    subgraph COMPARE_50["<b>COMPARE_50</b>"]
        direction TB
        FUNC["FUNC"]
        IN1["IN1"]
        IN2["IN2"]
        SENS["SENS"]
        STATUS["<span style='background:#ff0000;color:white;padding:4px 8px;border-radius:3px;font-weight:bold'>""" + str(status) + """</span>"]
        OUT["OUT"]
    end
    
    %% Output device on the right
    GT["GT<br/>(FALSE)"]
    
    %% Connections
    BT -.->|input| FUNC
    BZ23Y -.->|input| IN1
    LP45T -.->|input| IN2
    CONST -.->|input| SENS
    OUT -.->|output| GT
    
    %% Styling
    style COMPARE_50 fill:#e3f2fd,stroke:#1976d2,stroke-width:4px,color:#000
    style BT fill:#f5f5f5,stroke:#666,stroke-width:2px
    style BZ23Y fill:#f5f5f5,stroke:#666,stroke-width:2px
    style LP45T fill:#f5f5f5,stroke:#666,stroke-width:2px
    style CONST fill:#f5f5f5,stroke:#666,stroke-width:2px
    style GT fill:#ffebee,stroke:#c62828,stroke-width:2px
    style FUNC fill:#fff,stroke:#999,stroke-width:1px
    style IN1 fill:#fff,stroke:#999,stroke-width:1px
    style IN2 fill:#fff,stroke:#999,stroke-width:1px
    style SENS fill:#fff,stroke:#999,stroke-width:1px
    style OUT fill:#fff,stroke:#999,stroke-width:1px
    style STATUS fill:none,stroke:none
"""
    return mermaid

def generate_plc_move_block():
    """Generate a MOVE instruction block diagram"""
    mermaid = """flowchart LR
    subgraph inputs[" "]
        A[bz23y_a<br/>TRUE<br/>Value: 0]
        B[ENABLE<br/>TRUE]
    end
    
    subgraph MOVE_150["MOVE_150"]
        direction TB
        SRC[SRC]
        EN[EN]
        DEST[DEST<br/><span style='color:red'>2</span>]
    end
    
    subgraph outputs[" "]
        C[BZ23Y<br/>0.00 mils]
    end
    
    A --> SRC
    B --> EN
    DEST --> C
    
    style MOVE_150 fill:#e3f2fd,stroke:#1976d2,stroke-width:3px
    style A fill:#fff,stroke:#666,stroke-width:2px
    style B fill:#fff,stroke:#666,stroke-width:2px
    style C fill:#fff,stroke:#666,stroke-width:2px
"""
    return mermaid


def generate_plc_function_block(block_type, block_name, inputs, outputs, internal_values=None):
    """
    Generate a generic PLC function block diagram
    
    Args:
        block_type: Type of block (MOVE, ADD, SUB, MUL, DIV, TON, etc.)
        block_name: Instance name (e.g., MOVE_150)
        inputs: List of tuples [(name, device, value), ...]
        outputs: List of tuples [(name, device, value), ...]
        internal_values: Dict of internal indicators {name: value}
    """
    mermaid = "flowchart LR\n"
    
    # Input section
    if inputs:
        mermaid += '    subgraph inputs[" "]\n'
        for i, (name, device, value) in enumerate(inputs):
            node_id = f"IN{i}"
            mermaid += f"        {node_id}[{device}<br/>{name}<br/>Value: {value}]\n"
        mermaid += "    end\n\n"
    
    # Function block
    mermaid += f'    subgraph {block_name}["{block_name}"]\n'
    mermaid += "        direction TB\n"
    
    # Input pins
    for i, (name, _, _) in enumerate(inputs):
        pin_id = f"PIN_IN{i}"
        mermaid += f"        {pin_id}[{name}]\n"
    
    # Internal values
    if internal_values:
        for key, value in internal_values.items():
            mermaid += f"        INT_{key}[{key}<br/><span style='color:red'>{value}</span>]\n"
    
    # Output pins
    for i, (name, _, _) in enumerate(outputs):
        pin_id = f"PIN_OUT{i}"
        mermaid += f"        {pin_id}[{name}]\n"
    
    mermaid += "    end\n\n"
    
    # Output section
    if outputs:
        mermaid += '    subgraph outputs[" "]\n'
        for i, (name, device, value) in enumerate(outputs):
            node_id = f"OUT{i}"
            mermaid += f"        {node_id}[{device}<br/>{name}<br/>{value}]\n"
        mermaid += "    end\n\n"
    
    # Connections
    for i in range(len(inputs)):
        mermaid += f"    IN{i} --> PIN_IN{i}\n"
    
    for i in range(len(outputs)):
        mermaid += f"    PIN_OUT{i} --> OUT{i}\n"
    
    # Styling
    mermaid += f"\n    style {block_name} fill:#e3f2fd,stroke:#1976d2,stroke-width:3px\n"
    
    return mermaid


def generate_ladder_logic_rung(rung_number, contacts, coil):
    """
    Generate a ladder logic rung
    
    Args:
        rung_number: Rung number
        contacts: List of contact dicts [{"type": "NO/NC", "tag": "tag_name", "state": True/False}, ...]
        coil: Dict {"tag": "tag_name", "type": "normal/set/reset"}
    """
    mermaid = "flowchart LR\n"
    mermaid += f"    START{rung_number}(( )) --> "
    
    # Add contacts in series
    for i, contact in enumerate(contacts):
        node_id = f"C{rung_number}_{i}"
        contact_type = "NO" if contact["type"] == "NO" else "NC"
        state = "CLOSED" if contact["state"] else "OPEN"
        
        if contact["type"] == "NO":
            symbol = "| |" if contact["state"] else "|/|"
        else:
            symbol = "|/|" if contact["state"] else "| |"
        
        mermaid += f"{node_id}[{symbol}<br/>{contact['tag']}<br/>{state}]"
        
        if i < len(contacts) - 1:
            mermaid += " --> "
    
    # Add coil
    coil_symbol = "( )" if coil["type"] == "normal" else "(S)" if coil["type"] == "set" else "(R)"
    mermaid += f" --> COIL{rung_number}[{coil_symbol}<br/>{coil['tag']}]"
    mermaid += f" --> END{rung_number}(( ))\n"
    
    # Styling
    for i, contact in enumerate(contacts):
        color = "#4caf50" if contact["state"] else "#f44336"
        mermaid += f"    style C{rung_number}_{i} fill:{color},stroke:#333,color:#fff\n"
    
    return mermaid


# Example usage
if __name__ == "__main__":
    # Example 1: MOVE block (like your image)
    print("=== MOVE Block ===")
    print(generate_plc_move_block())
    print()
    
    # Example 2: Generic function block
    print("=== ADD Block ===")
    inputs = [
        ("IN1", "TEMP_SENSOR_1", "75.5"),
        ("IN2", "TEMP_SENSOR_2", "80.2")
    ]
    outputs = [
        ("OUT", "AVG_TEMP", "77.85")
    ]
    print(generate_plc_function_block("ADD", "ADD_100", inputs, outputs))
    print()
    
    # Example 3: Ladder logic rung
    print("=== Ladder Logic Rung ===")
    contacts = [
        {"type": "NO", "tag": "START_BTN", "state": True},
        {"type": "NC", "tag": "E_STOP", "state": True},
        {"type": "NO", "tag": "PRESSURE_OK", "state": True}
    ]
    coil = {"tag": "MOTOR_RUN", "type": "normal"}
    print(generate_ladder_logic_rung(1, contacts, coil))
