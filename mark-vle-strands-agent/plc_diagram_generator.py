"""
PLC-style Function Block Diagram Generator
Creates Mermaid diagrams that look like PLC ladder logic / FBD
"""

import re

def parse_plc_block_from_text(text):
    """
    Parse PLC block information from RAG text response
    Returns dict with block info
    """
    block_info = {
        'name': None,
        'type': None,
        'inputs': [],
        'outputs': [],
        'status': None
    }
    
    text_upper = text.upper()
    
    # Extract block name and type - check multiple variations
    if 'MOVE_150' in text_upper or 'MOVE-150' in text_upper or 'MOVE 150' in text_upper:
        block_info['name'] = 'MOVE_150'
        block_info['type'] = 'MOVE'
    elif 'COMPARE_50' in text_upper or 'COMPARE-50' in text_upper or 'COMPARE 50' in text_upper:
        block_info['name'] = 'COMPARE_50'
        block_info['type'] = 'COMPARE'
    elif 'MOVE' in text_upper and 'BLOCK' in text_upper:
        block_info['name'] = 'MOVE_150'
        block_info['type'] = 'MOVE'
    elif 'COMPARE' in text_upper and 'BLOCK' in text_upper:
        block_info['name'] = 'COMPARE_50'
        block_info['type'] = 'COMPARE'
    
    # Extract status code
    status_match = re.search(r'Status Code[:\s]+(\d+)', text, re.IGNORECASE)
    if status_match:
        block_info['status'] = status_match.group(1)
    
    # Parse pins from table or text
    lines = text.split('\n')
    for i, line in enumerate(lines):
        line_upper = line.upper()
        
        # Look for pin information
        if 'FUNC' in line_upper and 'BT' in line_upper:
            block_info['inputs'].append({'name': 'FUNC', 'device': 'BT', 'value': 'GT'})
        if 'SRC' in line_upper and ('BZ23Y_A' in line_upper or 'BZ23Y-A' in line_upper):
            block_info['inputs'].append({'name': 'SRC', 'device': 'bz23y_a', 'value': '0'})
        if ('EN' in line_upper or 'ENABLE' in line_upper) and 'INPUT' in line_upper:
            block_info['inputs'].append({'name': 'EN', 'device': 'ENABLE', 'value': 'TRUE'})
        if 'IN1' in line_upper and 'BZ23Y' in line_upper:
            value_match = re.search(r'(\d+\.?\d*)\s*mils?', line, re.IGNORECASE)
            value = value_match.group(1) if value_match else '0.00'
            block_info['inputs'].append({'name': 'IN1', 'device': 'BZ23Y', 'value': f'{value} mils'})
        if 'IN2' in line_upper and 'LP45T' in line_upper:
            value_match = re.search(r'(\d+\.?\d*)\s*mils?', line, re.IGNORECASE)
            value = value_match.group(1) if value_match else '7.4'
            block_info['inputs'].append({'name': 'IN2', 'device': 'LP45T', 'value': f'{value} mils'})
        if 'SENS' in line_upper and 'CONSTANT' in line_upper:
            block_info['inputs'].append({'name': 'SENS', 'device': 'Constant', 'value': '0'})
        if 'DEST' in line_upper and 'BZ23Y' in line_upper and 'OUTPUT' in line_upper:
            value_match = re.search(r'(\d+\.?\d*)\s*mils?', line, re.IGNORECASE)
            value = value_match.group(1) if value_match else '0.00'
            block_info['outputs'].append({'name': 'DEST', 'device': 'BZ23Y', 'value': f'{value} mils'})
        if 'OUT' in line_upper and 'GT' in line_upper and 'OUTPUT' in line_upper:
            block_info['outputs'].append({'name': 'OUT', 'device': 'GT', 'value': 'FALSE'})
    
    return block_info

def generate_plc_block_from_rag(text):
    """Generate PLC block diagram from RAG response text"""
    block_info = parse_plc_block_from_text(text)
    
    # If no block detected, return a message
    if not block_info['name']:
        return """flowchart TD
    A["No PLC block detected in response"]
    B["Try fetching: MOVE_150 or COMPARE_50"]
    A --> B
    style A fill:#ffebee,stroke:#c62828
    style B fill:#fff3e0,stroke:#ef6c00
"""
    
    if block_info['type'] == 'MOVE':
        return generate_move_block_dynamic(block_info)
    elif block_info['type'] == 'COMPARE':
        return generate_compare_block_dynamic(block_info)
    else:
        return generate_plc_move_block()  # Fallback

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
