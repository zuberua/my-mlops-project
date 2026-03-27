export interface BlockUsed {
  id: string;
  block: string;
  label: string;
  purpose: string;
  category: string;
  col: number;
  row: number;
  eqn?: string;
}

export interface Wire {
  from_block: string;
  from_pin: string;
  to_block: string;
  to_pin: string;
}

export interface VarInput {
  name: string;
  type: string;
  value: string;
  to_block: string;
  to_pin: string;
}

export interface ProgramDef {
  explanation: string;
  blocks_used: BlockUsed[];
  wires: Wire[];
  var_inputs: VarInput[];
  iec_notes: string[];
  source?: 'dynamodb' | 'agent';
  dependency_context?: {
    variable: string;
    scope: { prefix4: string[] | null; first_block: string | null };
    flow: Array<{
      depth: number;
      block: string;
      block_type: string;
      block_execution: string;
      pin: string;
      usage: string;
      connection: string;
      data_type: string;
    }>;
  };
}

export interface Message {
  role: 'user' | 'assistant';
  content: string;
  parsed?: ProgramDef;
  dynamodb_error?: string;
}
