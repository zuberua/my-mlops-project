import React, { useState, useRef, useEffect } from 'react';
import { Send, Cpu, GitBranch, Loader2 } from 'lucide-react';
import * as XLSX from 'xlsx';
import FBDCanvas from './FBDCanvas';
import { useChat } from './useChat';
import { Message, ProgramDef } from './types';
import './App.css';

type IOMapping = { device_tag: string; connected_variable: string };
type UnwrittenVariable = {
  variable: string;
  full_variable: string;
  where_used: string;
  description: string;
};

const EXAMPLES = [
  'Motor start/stop control with overload protection and run timer',
  'Gas turbine exhaust temperature monitoring with trip on high temp or spread',
  'Pressure control loop with high/low alarms and trip',
  'Vibration monitoring with alarm on 2 out of 4 sensors',
];

const SESSION_OPTIONS = [
  {
    id: 'custom-logic-development',
    title: 'Custom Logic Development',
    description:
      'Assign logic for I/O where standard logic is currently missing or unclear for some I/O.',
  },
  {
    id: 'library-hot-list-implementation',
    title: 'Library "Hot List" Implementation',
    description:
      'Integrate critical updates or hot list items for a specific library version not yet included in the standard release.',
  },
  {
    id: 'early-feature-adoption',
    title: 'Early Feature Adoption',
    description:
      'Implement features planned for future standard releases but required immediately for current project timelines.',
  },
  {
    id: 'new-custom-feature-support',
    title: 'New Custom Feature Support',
    description:
      'Develop customizations for new equipment as defined by project design documents.',
  },
];

function exportTaskListWorkbook(program: ProgramDef) {
  const inPins: Record<string, string[]> = {};
  const outPins: Record<string, string[]> = {};
  for (const b of program.blocks_used) {
    inPins[b.id] = [];
    outPins[b.id] = [];
  }
  for (const w of program.wires || []) {
    if (!outPins[w.from_block]?.includes(w.from_pin))
      outPins[w.from_block]?.push(w.from_pin);
    if (!inPins[w.to_block]?.includes(w.to_pin))
      inPins[w.to_block]?.push(w.to_pin);
  }
  for (const v of program.var_inputs || []) {
    if (!inPins[v.to_block]?.includes(v.to_pin))
      inPins[v.to_block]?.push(v.to_pin);
  }

  const controller = 'h1';
  const programName = 'p1';
  const taskName = 't1';

  const createBlocksRows: (string | number)[][] = [
    ['', '', '', '', '', '', 'Pin', 'Pin', 'Pin', 'Attribute', 'Attribute', 'Attribute'],
    [
      'Controller', 'ProgramName', 'TaskName', 'BlockName', 'BlockType',
      'BlockDataType', 'IN1', 'IN2', 'OUT', 'Device', 'AttName1', 'AttName2',
    ],
    ...program.blocks_used.map((b) => [
      controller, programName, taskName, b.id, b.block, 'bool',
      inPins[b.id]?.[0] || '', inPins[b.id]?.[1] || '',
      outPins[b.id]?.[0] || '', '', '', '',
    ]),
  ];

  const taskListRows: (string | number)[][] = [
    [
      'TaskName', 'LibTaskType', 'Controller', 'ProgGroupName',
      'ProgramName', 'ScreenObjName', 'ScreenName', 'LinkObjName', 'LinkScreenName',
    ],
    [taskName, '', controller, '', programName, '', '', '', ''],
  ];

  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet(taskListRows), 'TaskList');
  XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet(createBlocksRows), 'create_blocks');
  XLSX.writeFile(wb, 'TaskList_export.xlsx');
}

function ChatMessage({ m }: { m: Message }) {
  const parsed: any = m.role === 'assistant' ? (m as any).parsed : null;
  const dep = parsed?.dependency_context;

  return (
    <div className={`message ${m.role}`}>
      <div className="message-label">{m.role === 'user' ? 'You' : 'Agent'}</div>
      {m.role === 'assistant' && m.dynamodb_error && (
        <div className="dynamodb-error-banner">
          ⚠️ DynamoDB KB unavailable: {m.dynamodb_error} — using agent knowledge instead.
        </div>
      )}
      {m.role === 'assistant' && parsed ? (
        <div className="agent-response">
          {parsed.source && (
            <span className={`source-badge ${parsed.source}`}>
              {parsed.source === 'dynamodb' ? '📊 DynamoDB KB' : '🤖 Agent Knowledge'}
            </span>
          )}
          <p>{parsed.explanation}</p>
          {Array.isArray(dep?.flow) && dep.flow.length > 0 && (
            <div className="dep-kb-panel">
              <strong>Dependency KB (trace) for {dep.variable}</strong>
              <div className="io-upload-sub">
                Scope:&nbsp;
                {dep.scope?.prefix4 ? dep.scope.prefix4.join(' | ') : '—'}
                {dep.scope?.first_block ? ` · ${dep.scope.first_block}` : ''}
              </div>
              <div className="io-table-wrap">
                <table className="io-table">
                  <thead>
                    <tr>
                      <th>Depth</th><th>Block</th><th>Type</th><th>Exec</th>
                      <th>Pin</th><th>Usage</th><th>Connection</th><th>DataType</th>
                    </tr>
                  </thead>
                  <tbody>
                    {dep.flow.slice(0, 200).map((r: any, i: number) => (
                      <tr key={i}>
                        <td>{r.depth}</td><td>{r.block}</td><td>{r.block_type}</td>
                        <td>{r.block_execution}</td><td>{r.pin}</td><td>{r.usage}</td>
                        <td>{r.connection}</td><td>{r.data_type}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
          <div className="blocks-used">
            <strong>Blocks:</strong>
            {parsed.blocks_used?.map((b: any) => (
              <span key={b.id} className="block-tag" title={b.purpose}>
                {b.block}
              </span>
            ))}
          </div>
          {parsed.iec_notes?.length > 0 && (
            <ul className="iec-notes">
              {parsed.iec_notes.map((n: string, j: number) => (
                <li key={j}>{n}</li>
              ))}
            </ul>
          )}
        </div>
      ) : (
        <div className="message-text">{m.content}</div>
      )}
    </div>
  );
}

export default function App() {
  const { messages, loading, program, sendMessage } = useChat();
  const [input, setInput] = useState('');
  const [sessionOption, setSessionOption] = useState<string>('');
  const [sessionOptionId, setSessionOptionId] = useState<string>('');
  const [ioReady, setIoReady] = useState(false);
  const [ioStatus, setIoStatus] = useState('Upload current project I/O variable report (.csv) to continue.');
  const [ioSummary, setIoSummary] = useState('');
  const [ioMappings, setIoMappings] = useState<IOMapping[]>([]);
  const [codingReady, setCodingReady] = useState(false);
  const [codingStatus, setCodingStatus] = useState('Upload CodingPracticeReport CSV for unresolved variable extraction.');
  const [codingSummary, setCodingSummary] = useState('');
  const [unwrittenVariables, setUnwrittenVariables] = useState<UnwrittenVariable[]>([]);
  const [showSetup, setShowSetup] = useState(true);
  const [varFilter, setVarFilter] = useState('');
  const [selectedVariable, setSelectedVariable] = useState<UnwrittenVariable | null>(null);
  const [rightMode, setRightMode] = useState<'io-review' | 'workspace'>('workspace');
  const [varSortBy, setVarSortBy] = useState<'variable' | 'where_used' | 'description'>('variable');
  const [varSortDir, setVarSortDir] = useState<'asc' | 'desc'>('asc');
  const chatEndRef = useRef<HTMLDivElement>(null);
  const sessionIdRef = useRef(
    `session-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
  );

  const API = process.env.REACT_APP_API_URL || 'http://localhost:8001';
  const requiresCodingReport = sessionOptionId === 'custom-logic-development';
  const hasSelectedTarget = !requiresCodingReport || !!selectedVariable;
  const readyForChat =
    !!sessionOption && ioReady && (!requiresCodingReport || codingReady) && hasSelectedTarget;

  const variableKey = (v: UnwrittenVariable) =>
    `${v.variable}|${v.full_variable}|${v.where_used}|${v.description}`;

  const filteredUnwrittenVariables = unwrittenVariables.filter((v) => {
    const q = varFilter.trim().toLowerCase();
    if (!q) return true;
    return [v.variable, v.full_variable, v.where_used, v.description].some((s) =>
      s.toLowerCase().includes(q)
    );
  });

  const sortedUnwrittenVariables = [...filteredUnwrittenVariables].sort((a, b) => {
    const aVal = (a[varSortBy] || '').toLowerCase();
    const bVal = (b[varSortBy] || '').toLowerCase();
    const cmp = aVal.localeCompare(bVal, undefined, { numeric: true, sensitivity: 'base' });
    return varSortDir === 'asc' ? cmp : -cmp;
  });

  const selectedIndex = selectedVariable
    ? unwrittenVariables.findIndex((v) => variableKey(v) === variableKey(selectedVariable))
    : -1;
  const hasNextVariable = selectedIndex >= 0 && selectedIndex < unwrittenVariables.length - 1;

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    if (readyForChat) setShowSetup(false);
  }, [readyForChat]);

  function parseCSV(text: string): string[][] {
    const rows: string[][] = [];
    let row: string[] = [];
    let cell = '';
    let inQuotes = false;
    for (let i = 0; i < text.length; i += 1) {
      const ch = text[i];
      const next = text[i + 1];
      if (ch === '"') {
        if (inQuotes && next === '"') { cell += '"'; i += 1; }
        else { inQuotes = !inQuotes; }
        continue;
      }
      if (ch === ',' && !inQuotes) { row.push(cell.trim()); cell = ''; continue; }
      if ((ch === '\n' || ch === '\r') && !inQuotes) {
        if (ch === '\r' && next === '\n') i += 1;
        row.push(cell.trim());
        if (row.some((c) => c.length > 0)) rows.push(row);
        row = []; cell = ''; continue;
      }
      cell += ch;
    }
    if (cell.length > 0 || row.length > 0) {
      row.push(cell.trim());
      if (row.some((c) => c.length > 0)) rows.push(row);
    }
    return rows;
  }

  async function syncSessionMemory(mappings: IOMapping[], unwrittenVars: UnwrittenVariable[]) {
    const res = await fetch(`${API}/session/io-report`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionIdRef.current,
        enhancement_option: sessionOption,
        mappings,
        unwritten_variables: unwrittenVars,
      }),
    });
    if (!res.ok) throw new Error('Failed to store session memory in backend.');
  }

  function handleSessionOptionSelect(optionId: string, optionTitle: string) {
    setShowSetup(true);
    setSessionOptionId(optionId);
    setSessionOption(optionTitle);
    setIoReady(false); setIoSummary(''); setIoMappings([]);
    setIoStatus('Upload current project I/O variable report (.csv) to continue.');
    setCodingReady(false); setCodingSummary('');
    setVarSortBy('variable'); setVarSortDir('asc');
    setUnwrittenVariables([]); setSelectedVariable(null);
    setRightMode(optionId === 'custom-logic-development' ? 'io-review' : 'workspace');
    setCodingStatus('Upload CodingPracticeReport CSV for unresolved variable extraction.');
  }

  function handleSend() {
    if (!readyForChat) return;
    sendMessage(input, sessionOption, sessionIdRef.current);
    setInput('');
  }

  async function handleIOUpload(file: File | null) {
    if (!file || !sessionOption) return;
    if (!file.name.toLowerCase().endsWith('.csv')) {
      setIoReady(false); setIoSummary('');
      setIoStatus('Invalid file type. Please upload a CSV file in the I/O Variable Report format.');
      return;
    }
    try {
      setIoStatus('Validating uploaded I/O report...');
      const text = await file.text();
      const rows = parseCSV(text);
      if (rows.length < 2) throw new Error('CSV file is too short.');
      let headerIdx = 0;
      while (headerIdx < rows.length && (rows[headerIdx][0] || '').startsWith('#'))
        headerIdx += 1;
      if (headerIdx >= rows.length) throw new Error('Could not locate a header row.');
      const headers = rows[headerIdx].map((h) => (h || '').trim().toLowerCase());
      const deviceIdx = headers.indexOf('device tag');
      const connectedIdx = headers.indexOf('connected variable');
      if (deviceIdx === -1 || connectedIdx === -1) {
        throw new Error('Missing required columns: Device Tag and Connected Variable.');
      }
      const seen = new Set<string>();
      const mappings: Array<{ device_tag: string; connected_variable: string }> = [];
      for (let i = headerIdx + 1; i < rows.length; i += 1) {
        const cols = rows[i];
        const device = (cols[deviceIdx] || '').trim();
        const connected = (cols[connectedIdx] || '').trim();
        if (!device || !connected) continue;
        const key = `${device}|||${connected}`;
        if (seen.has(key)) continue;
        seen.add(key);
        mappings.push({ device_tag: device, connected_variable: connected });
      }
      if (!mappings.length) {
        throw new Error('No valid Device Tag → Connected Variable mappings found.');
      }
      await syncSessionMemory(mappings, unwrittenVariables);
      setIoMappings(mappings);
      setIoReady(true);
      setIoSummary(`Loaded ${mappings.length} unique mappings from ${file.name}.`);
      setIoStatus('I/O report validated and stored in session memory. You can start chat now.');
    } catch (err) {
      setIoReady(false); setIoSummary('');
      setIoStatus(err instanceof Error ? err.message : 'Failed to validate I/O report.');
    }
  }

  async function handleCodingReportUpload(file: File | null) {
    if (!file || !sessionOption || !requiresCodingReport) return;
    if (!file.name.toLowerCase().endsWith('.csv')) {
      setCodingReady(false); setCodingSummary('');
      setCodingStatus('Invalid file type. Please upload CodingPracticeReport CSV.');
      return;
    }
    try {
      setCodingStatus('Parsing CodingPracticeReport...');
      const text = await file.text();
      const rows = parseCSV(text);
      const start = rows.findIndex((r) => r.some((c) => /unwritten\s+variables/i.test(c)));
      const end = rows.findIndex(
        (r, idx) => idx > start && r.some((c) => /multiple\s+writes/i.test(c))
      );
      if (start === -1 || end === -1 || end <= start + 1) {
        throw new Error('Could not find Unwritten Variables section between markers.');
      }
      const section = rows.slice(start + 1, end);
      const headerIdx = section.findIndex((r) =>
        r.some((c) => /variable|where\s*used|description/i.test(c))
      );
      if (headerIdx === -1)
        throw new Error('Could not find header row in Unwritten Variables section.');
      const headers = section[headerIdx].map((h) => h.toLowerCase());
      const varIdx = headers.findIndex((h) => h.includes('variable'));
      const whereIdx = headers.findIndex((h) => h.includes('where') && h.includes('used'));
      const descIdx = headers.findIndex((h) => h.includes('description'));
      const dataRows = section.slice(headerIdx + 1);
      const seen = new Set<string>();
      const out: UnwrittenVariable[] = [];
      for (const r of dataRows) {
        const source = varIdx >= 0 ? r[varIdx] || '' : r.join(' ');
        const varMatch = source.match(/\b([da]_[A-Za-z0-9_]+)\b/i);
        if (!varMatch) continue;
        const shortVar = varMatch[1];
        const fullMatch = source.match(/\b([A-Za-z0-9_]+\.[da]_[A-Za-z0-9_]+)\b/i);
        const fullVar = fullMatch ? fullMatch[1] : source;
        const whereUsed = whereIdx >= 0 ? r[whereIdx] || '' : '';
        const description = descIdx >= 0 ? r[descIdx] || '' : '';
        const key = `${shortVar}|${whereUsed}|${description}`;
        if (seen.has(key)) continue;
        seen.add(key);
        out.push({ variable: shortVar, full_variable: fullVar, where_used: whereUsed, description });
      }
      if (!out.length)
        throw new Error('No d_*/a_* variables found in Unwritten Variables section.');
      await syncSessionMemory(ioMappings, out);
      setUnwrittenVariables(out);
      setSelectedVariable(null);
      setRightMode('io-review');
      setCodingReady(true);
      setCodingSummary(`Extracted ${out.length} unresolved d_/a_ variables from ${file.name}.`);
      setCodingStatus('Coding practice report parsed and stored. Select any variable below to proceed.');
    } catch (err) {
      setCodingReady(false); setCodingSummary('');
      setCodingStatus(err instanceof Error ? err.message : 'Failed to parse CodingPracticeReport.');
    }
  }

  function proceedWithVariable(v: UnwrittenVariable) {
    const msg =
      `Assign logic for unresolved variable ${v.variable} (full: ${v.full_variable}). ` +
      `Where used: ${v.where_used || 'N/A'}. Description: ${v.description || 'N/A'}. ` +
      `STEP 1: Run dep_trace("${v.variable}") to trace signal chain dependencies from the Pins KB. ` +
      `STEP 2: If dep_trace returns flow data, use the traced blocks and wiring to build the FBD. ` +
      `If dep_trace returns empty/error, fall back to IO report lookups and block catalog search to design the logic. ` +
      `Generate the complete FBD JSON with blocks_used, wires, var_inputs, and dependency_context.`;
    setSelectedVariable(v);
    setRightMode('workspace');
    setInput(msg);
    const canSend =
      !!sessionOption && ioReady && (!requiresCodingReport || (codingReady && !!v));
    if (canSend) {
      sendMessage(msg, sessionOption, sessionIdRef.current);
      setInput('');
    }
  }

  function toggleVarSort(key: 'variable' | 'where_used' | 'description') {
    if (varSortBy === key) {
      setVarSortDir((prev) => (prev === 'asc' ? 'desc' : 'asc'));
      return;
    }
    setVarSortBy(key);
    setVarSortDir('asc');
  }

  function proceedNextVariable() {
    if (!(selectedIndex >= 0 && selectedIndex < unwrittenVariables.length - 1)) return;
    proceedWithVariable(unwrittenVariables[selectedIndex + 1]);
  }

  return (
    <div className="app">
      <header className="header">
        <Cpu size={20} color="#4a9eff" />
        <span className="header-title">GE Mark VIe Programming Agent</span>
        <span className="header-sub">IEC 61131-3 FBD · GEI-100682 Block Library</span>
      </header>

      <div className="main">
        <div className="chat-panel">
          <div className="chat-messages">
            {sessionOption && !showSetup && (
              <div className="setup-minibar">
                <span>Setup complete</span>
                <button className="mini-link-btn" onClick={() => setShowSetup(true)}>
                  Review Setup
                </button>
              </div>
            )}

            {showSetup && (
              <div className="setup-card">
                <div className="setup-card-head">
                  <h3>Setup</h3>
                  {sessionOption && (
                    <button className="mini-link-btn" onClick={() => setShowSetup(false)}>
                      Minimize
                    </button>
                  )}
                </div>
                <div className="setup-steps">
                  <span className={`setup-step ${sessionOption ? 'done' : ''}`}>1. Option</span>
                  <span className={`setup-step ${ioReady ? 'done' : ''}`}>2. I/O Report</span>
                  {requiresCodingReport && (
                    <span className={`setup-step ${codingReady ? 'done' : ''}`}>
                      3. Coding Report
                    </span>
                  )}
                </div>

                {!sessionOption && (
                  <div className="session-selector">
                    <h3>Select Enhancement Path</h3>
                    <p>Choose one option before starting chat.</p>
                    <div className="session-options">
                      {SESSION_OPTIONS.map((option) => (
                        <button
                          key={option.id}
                          className="session-option-btn"
                          onClick={() => handleSessionOptionSelect(option.id, option.title)}
                        >
                          <span className="session-option-title">{option.title}</span>
                          <span className="session-option-desc">{option.description}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {sessionOption && (
                  <div className="selected-session-banner">
                    <strong>Selected:</strong> {sessionOption}
                  </div>
                )}

                {/* Upload #1: I/O Variable Report */}
                {sessionOption && (
                  <div className="io-upload-panel">
                    <div className="io-upload-title">Upload Current Project I/O Variable Report</div>
                    <div className="io-upload-sub">
                      Format reference: <code>samples/G1 IO Variable Report.csv</code>
                    </div>
                    <label className="io-file-label">
                      <input
                        type="file"
                        accept=".csv,text/csv"
                        onChange={(e) => handleIOUpload(e.target.files?.[0] || null)}
                      />
                    </label>
                    <div className={`io-upload-status ${ioReady ? 'ok' : ''}`}>{ioStatus}</div>
                    {ioSummary && <div className="io-upload-summary">{ioSummary}</div>}
                  </div>
                )}

                {/* Upload #2: Coding Practice Report */}
                {requiresCodingReport && (
                  <div className="io-upload-panel">
                    <div className="io-upload-title">Upload Coding Practice Report</div>
                    <div className="io-upload-sub">
                      Expected section markers: <code>Unwritten Variables</code> to{' '}
                      <code>Multiple Writes</code>
                    </div>
                    <label className="io-file-label">
                      <input
                        type="file"
                        accept=".csv,text/csv"
                        onChange={(e) => handleCodingReportUpload(e.target.files?.[0] || null)}
                      />
                    </label>
                    <div className={`io-upload-status ${codingReady ? 'ok' : ''}`}>
                      {codingStatus}
                    </div>
                    {codingSummary && <div className="io-upload-summary">{codingSummary}</div>}
                    {unwrittenVariables.length > 0 && (
                      <div className="io-upload-sub">
                        {unwrittenVariables.length} unresolved variables available. Review and
                        proceed from right panel I/O Review.
                      </div>
                    )}
                  </div>
                )}

              </div>
            )}

            {messages.length === 0 && readyForChat && (
              <div className="welcome">
                <Cpu size={36} color="#4a9eff" />
                <h3>Mark VIe Programming Agent</h3>
                <p>
                  Describe your control use case. The agent designs a complete IEC 61131-3 FBD
                  program using the Mark VIe block library.
                </p>
                <div className="examples">
                  {EXAMPLES.map((ex) => (
                    <button key={ex} className="example-btn" onClick={() => setInput(ex)}>
                      {ex}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((m, i) => (
              <ChatMessage key={i} m={m} />
            ))}

            {loading && (
              <div className="message assistant">
                <div className="message-label">Agent</div>
                <div
                  className="message-text"
                  style
={{ display: 'flex', alignItems: 'center', gap: 8 }}
                >
                  <Loader2 size={14} className="spin" /> {(() => {
                    const lastUser = [...messages].reverse().find(m => m.role === 'user');
                    const txt = lastUser?.content?.toLowerCase() || '';
                    const isQuestion = /\b(what|why|how|explain|describe|tell|does|is it|which|where|can you)\b/.test(txt);
                    return isQuestion ? 'Thinking...' : 'Designing program...';
                  })()}
                </div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          <div className="input-area">
            <textarea
              className="input-box"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              placeholder={
                sessionOption
                  ? readyForChat
                    ? 'Describe your control use case... (Enter to send)'
                    : 'Complete required uploads to begin chat'
                  : 'Select an enhancement path to begin'
              }
              rows={3}
              disabled={!readyForChat}
            />
            <button
              className="send-btn"
              onClick={handleSend}
              disabled={loading || !readyForChat}
            >
              {loading ? <Loader2 size={16} className="spin" /> : <Send size={16} />}
            </button>
          </div>
        </div>

        <div className="diagram-panel">
          <div className="tabs">
            {requiresCodingReport && (
              <button
                className={`tab ${rightMode === 'io-review' ? 'active' : ''}`}
                onClick={() => setRightMode('io-review')}
              >
                I/O Review
              </button>
            )}
            <button
              className={`tab ${rightMode === 'workspace' ? 'active' : ''}`}
              onClick={() => setRightMode('workspace')}
            >
              <GitBranch size={13} /> FBD Workspace
            </button>
            {program && (
              <span
                style={{
                  marginLeft: 'auto',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  padding: '0 12px',
                }}
              >
                <span style={{ fontSize: 11, color: '#666' }}>
                  {program.blocks_used?.length} blocks · {program.wires?.length} wires
                </span>
                <button className="view-btn" onClick={() => exportTaskListWorkbook(program)}>
                  ⬇ Export Excel
                </button>
              </span>
            )}
          </div>

          <div className="diagram-scroll">
            {requiresCodingReport && rightMode === 'io-review' && (
              <div className="io-review-panel">
                <div className="io-review-head">
                  <h3>Unwritten Variables</h3>
                  {selectedVariable && (
                    <span className="io-review-picked">
                      Selected: {selectedVariable.variable}
                    </span>
                  )}
                </div>
                <input
                  className="var-filter-input"
                  placeholder="Filter variables, where used, description..."
                  value={varFilter}
                  onChange={(e) => setVarFilter(e.target.value)}
                />
                <div className="io-upload-sub">
                  Showing {sortedUnwrittenVariables.length} of {unwrittenVariables.length}
                </div>

                <div className="io-table-wrap">
                  <table className="io-table">
                    <thead>
                      <tr>
                        <th>
                          <button className="sort-btn" onClick={() => toggleVarSort('variable')}>
                            Variable
                          </button>
                        </th>
                        <th>
                          <button className="sort-btn" onClick={() => toggleVarSort('where_used')}>
                            Where Used
                          </button>
                        </th>
                        <th>
                          <button
                            className="sort-btn"
                            onClick={() => toggleVarSort('description')}
                          >
                            Description
                          </button>
                        </th>
                        <th>Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {sortedUnwrittenVariables.map((v, idx) => (
                        <tr
                          key={`${v.variable}-${idx}`}
                          className={
                            selectedVariable &&
                            variableKey(selectedVariable) === variableKey(v)
                              ? 'selected'
                              : ''
                          }
                        >
                          <td>
                            <div className="table-var">{v.variable}</div>
                            <div className="table-sub">{v.full_variable}</div>
                          </td>
                          <td>{v.where_used || 'N/A'}</td>
                          <td>{v.description || 'N/A'}</td>
                          <td>
                            <button
                              className="proceed-link-btn"
                              onClick={() => proceedWithVariable(v)}
                            >
                              Assign Logic
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {(!requiresCodingReport || rightMode === 'workspace') && (
              <>
                {requiresCodingReport && !selectedVariable && (
                  <div className="empty-diagram">
                    <p>Select a variable in I/O Review and click Assign Logic.</p>
                  </div>
                )}
                {selectedVariable && (
                  <div className="selected-session-banner" style={{ marginBottom: 10 }}>
                    <strong>Target Variable:</strong> {selectedVariable.variable} |{' '}
                    {selectedVariable.where_used || 'N/A'}
                    <button
                      className="next-var-btn"
                      onClick={proceedNextVariable}
                      disabled={!hasNextVariable}
                    >
                      Next unresolved
                    </button>
                  </div>
                )}
                {program ? (
                  <FBDCanvas program={program} />
                ) : (
                  <div className="empty-diagram">
                    <GitBranch size={44} color="#333" />
                    <p>FBD diagram will appear here</p>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
