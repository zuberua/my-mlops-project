#!/usr/bin/env python3
"""
Example: How another agent would use Mark Vle Strands Agent

This demonstrates the workflow for an external agent to:
1. Search the Mark Vle knowledge base
2. Generate PLC block diagrams
3. Process the results
"""

from client import MarkVleClient

def main():
    """Example workflow for another agent"""
    
    print("="*60)
    print("External Agent Using Mark Vle Strands Agent")
    print("="*60)
    
    # Step 1: Connect to Mark Vle Agent
    print("\n[Step 1] Connecting to Mark Vle Agent...")
    client = MarkVleClient()
    
    # Step 2: Search for information about a block
    print("\n[Step 2] Searching for COMPARE_50 information...")
    block_name = "COMPARE_50"
    info = client.chat(f"Tell me about {block_name}")
    print(f"Response:\n{info[:300]}...\n")
    
    # Step 3: Generate diagram for the block
    print(f"[Step 3] Generating diagram for {block_name}...")
    mermaid_code, block_info = client.generate_diagram(block_name)
    print(f"✓ Generated Mermaid diagram ({len(mermaid_code)} chars)")
    print(f"✓ Retrieved block info ({len(block_info)} chars)")
    
    # Step 4: Save diagram to file
    print(f"\n[Step 4] Saving diagram to file...")
    output_file = f"/tmp/{block_name.lower()}_diagram.mmd"
    with open(output_file, 'w') as f:
        f.write(mermaid_code)
    print(f"✓ Saved to {output_file}")
    
    # Step 5: Process multiple blocks
    print("\n[Step 5] Processing multiple blocks...")
    blocks = ["COMPARE_50", "MOVE_150", "TNH-SPEED-1"]
    
    for block in blocks:
        try:
            print(f"\n  Processing {block}...")
            mermaid, info = client.generate_diagram(block)
            
            # Save each diagram
            filename = f"/tmp/{block.lower()}_diagram.mmd"
            with open(filename, 'w') as f:
                f.write(mermaid)
            
            print(f"  ✓ {block}: Diagram saved to {filename}")
            
        except Exception as e:
            print(f"  ✗ {block}: Error - {e}")
    
    # Step 6: Get agent configuration
    print("\n[Step 6] Checking agent configuration...")
    config = client.get_config()
    print(f"  S3 Bucket: {config['s3Bucket']}")
    print(f"  AWS Region: {config['awsRegion']}")
    print(f"  Embedding Model: {config['embeddingModel']}")
    
    print("\n" + "="*60)
    print("✓ External agent workflow completed successfully!")
    print("="*60)


if __name__ == '__main__':
    try:
        main()
    except ConnectionError as e:
        print(f"\n✗ Error: {e}")
        print("\nMake sure Mark Vle Agent is running:")
        print("  cd mark-vle-strands-agent")
        print("  ./start.sh")
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
