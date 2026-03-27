import React, { useMemo, useRef, useState, useCallback, useEffect } from 'react';
import { ProgramDef } from './types';

const COL_W = 300;
const ROW_H = 220;
const VAR_X = 10;
const BLOCK_OFFSET_X = 180;
type Shape = 'circle' | 'and' | 'or' | 'not' | 'rect';

function getShape(block: string): Shape {
  const b = block.toUpperCase();
  if (['ABS','ADD','CALC','AVRG','DIV','MULT','SUB','NEGATE','DERIVATIVE','INTEG','INTWLEAD','FIR','IIR','TRNFUN'].includes(b)) return 'circle';
  if (b === 'AND') return 'and';
  if (['OR','XOR','XNOR'].includes(b)) return 'or';
  if (b === 'NOT') return 'not';
  return 'rect';
}

const CIRCLE_SYM: Record<string, string> = {
  ABS: '|x|', ADD: '\u03A3', CALC: 'f(x)', AVRG: 'x\u0304', DIV: '\u00F7', MULT: '\u00D7',
  SUB: '\u2212', NEGATE: '\u2212x', DERIVATIVE: 'd/dt', INTEG: '\u222B', FIR: 'FIR', IIR: 'IIR', TRNFUN: 'H(z)',
};

const CAT_COLOR: Record<string, { bg: string; stroke: string }> = {
  Math: { bg: '#dce8ff', stroke: '#003366' },
  Array: { bg: '#dcf0dc', stroke: '#1a5c1a' },
  Comparison: { bg: '#fff0dc', stroke: '#7a3000' },
  'Boolean Operations': { bg: '#ede0ff', stroke: '#4a0080' },
  Sequencing: { bg: '#fff5dc', stroke: '#5c3a00' },
  'Controls (Basic)': { bg: '#ffeaea', stroke: '#800000' },
  System: { bg: '#e8f8ff', stroke: '#005c7a' },
  'Timers and Counters': { bg: '#f0ffe8', stroke: '#2a5c00' },
};
const DEF_COLOR = { bg: '#f0f0f0', stroke: '#444' };

function shapeGeometry(shape: Shape, ins: string[], outs: string[]) {
  const pinGap = 28;
  switch (shape) {
    case 'circle': {
      const R = 44;
      const cx = R + 2, cy = R + 2;
      const inPorts = ins.map((p, i) => ({ pin: p, x: cx - R, y: cy - ((ins.length - 1) * 18) / 2 + i * 18 }));
      const outPorts = outs.map((p, i) => ({ pin: p, x: cx + R, y: cy - ((outs.length - 1) * 18) / 2 + i * 18 }));
      return { w: (cx + R + 2) * 2, h: cy + R + 2, cx, cy, R, inPorts, outPorts };
    }
    case 'and': {
      const h = Math.max(ins.length, 1) * pinGap + 20;
      const w = 90;
      const inPorts = ins.map((p, i) => ({ pin: p, x: 0, y: 10 + i * pinGap }));
      const outPorts = outs.map((p) => ({ pin: p, x: w + 2, y: h / 2 }));
      return { w: w + 2, h, inPorts, outPorts };
    }
    case 'or': {
      const h = Math.max(ins.length, 1) * pinGap + 20;
      const w = 90;
      const inPorts = ins.map((p, i) => ({ pin: p, x: 0, y: 10 + i * pinGap }));
      const outPorts = outs.map((p) => ({ pin: p, x: w + 2, y: h / 2 }));
      return { w: w + 2, h, inPorts, outPorts };
    }
    case 'not': {
      const h = Math.max(ins.length, outs.length, 1) * 28 + 20;
      const w = 90;
      const inPorts = ins.map((p, i) => ({ pin: p, x: 0, y: 10 + (h - 20) / (ins.length + 1) * (i + 1) }));
      const outPorts = outs.map((p, i) => ({ pin: p, x: w + 10, y: 10 + (h - 20) / (outs.length + 1) * (i + 1) }));
      return { w: w + 10, h, inPorts, outPorts };
    }
    default: {
      const rows = Math.max(ins.length, outs.length, 1);
      const h = rows * pinGap + 36;
      const w = 160;
      const inPorts = ins.map((p, i) => ({ pin: p, x: 0, y: 36 + i * pinGap + pinGap / 2 }));
      const outPorts = outs.map((p, i) => ({ pin: p, x: w, y: 36 + i * pinGap + pinGap / 2 }));
      return { w, h, inPorts, outPorts };
    }
  }
}

function renderShape(
  shape: Shape, geo: any, block: string, label: string,
  col: { bg: string; stroke: string }, eqn?: string
) {
  const { bg, stroke } = col;
  switch (shape) {
    case 'circle': {
      const { cx, cy, R } = geo;
      const sym = CIRCLE_SYM[block.toUpperCase()] || block;
      return (
        <>
          <circle cx={cx} cy={cy} r={R} fill={bg} stroke={stroke} strokeWidth={2.5} />
          <text x={cx} y={cy - 6} textAnchor="middle" fontSize={13} fontWeight="bold" fill={stroke}>{sym}</text>
          <text x={cx} y={cy + 8} textAnchor="middle" fontSize={10} fontWeight="bold" fill={stroke} fontFamily="monospace">{block}</text>
          <text x={cx} y={cy + 20} textAnchor="middle" fontSize={8} fill={stroke} fontFamily="monospace">{label}</text>
        </>
      );
    }
    case 'and': {
      const { w, h } = geo;
      const mid = w - 2;
      const path = `M 0 0 L ${mid * 0.55} 0 Q ${mid} ${h / 2} ${mid * 0.55} ${h} L 0 ${h} Z`;
      return (
        <>
          <path d={path} fill={bg} stroke={stroke} strokeWidth={2.5} />
          <text x={mid * 0.28} y={h / 2} textAnchor="middle" fontSize={11} fontWeight="bold" fill={stroke} fontFamily="monospace">AND</text>
          <text x={mid * 0.28} y={h / 2 + 13} textAnchor="middle" fontSize={8} fill={stroke} fontFamily="monospace">{label}</text>
        </>
      );
    }
    case 'or': {
      const { w, h } = geo;
      const mid = w - 2;
      const path = `M 0 0 Q 20 0 ${mid} ${h / 2} Q 20 ${h} 0 ${h} Q 18 ${h / 2} 0 0 Z`;
      return (
        <>
          <path d={path} fill={bg} stroke={stroke} strokeWidth={2.5} />
          <text x={mid * 0.42} y={h / 2} textAnchor="middle" fontSize={10} fontWeight="bold" fill={stroke} fontFamily="monospace">{block}</text>
          <text x={mid * 0.42} y={h / 2 + 13} textAnchor="middle" fontSize={8} fill={stroke} fontFamily="monospace">{label}</text>
        </>
      );
    }
    case 'not': {
      const { h } = geo;
      return (
        <>
          <polygon points={`0,0 70,${h / 2} 0,${h}`} fill={bg} stroke={stroke} strokeWidth={2.5} />
          <circle cx={78} cy={h / 2} r={8} fill={bg} stroke={stroke} strokeWidth={2.5} />
          <text x={28} y={h / 2 + 5} textAnchor="middle" fontSize={9} fontWeight="bold" fill={stroke} fontFamily="monospace">NOT</text>
        </>
      );
    }
    default: {
      const { w, h } = geo;
      return (
        <>
          <rect x={0} y={0} width={w} height={h} rx={5} fill={bg} stroke={stroke} strokeWidth={2} />
          <rect x={0} y={0} width={w} height={34} rx={5} fill={stroke} />
          <rect x={0} y={29} width={w} height={5} fill={stroke} />
          <text x={w / 2} y={13} textAnchor="middle" fontSize={10} fontWeight="bold" fill="white" fontFamily="monospace">{block}</text>
          <text x={w / 2} y={27} textAnchor="middle" fontSize={9} fill="#ddd" fontFamily="monospace">{label}</text>
          {eqn && (
            <text x={w / 2} y={h / 2 + 18} textAnchor="middle" fontSize={10} fontWeight="bold" fill={stroke} fontFamily="monospace">{eqn}</text>
          )}
        </>
      );
    }
  }
}

function renderPinLabels(shape: Shape, geo: any, _col: { bg: string; stroke: string }) {
  if (shape === 'rect') {
    return (
      <>
        {geo.inPorts.map((p: any) => (
          <text key={`il_${p.pin}`} x={p.x + 6} y={p.y + 4} fontSize={9} fill="#cc2200" fontFamily="monospace">{p.pin}</text>
        ))}
        {geo.outPorts.map((p: any) => (
          <text key={`ol_${p.pin}`} x={p.x - 6} y={p.y + 4} fontSize={9} fill="#006622" fontFamily="monospace" textAnchor="end">{p.pin}</text>
        ))}
      </>
    );
  }
  return (
    <>
      {geo.inPorts.map((p: any) => (
        <text key={`il_${p.pin}`} x={p.x - 4} y={p.y + 4} fontSize={8} fill="#cc2200" fontFamily="monospace" textAnchor="end">{p.pin}</text>
      ))}
      {geo.outPorts.map((p: any) => (
        <text key={`ol_${p.pin}`} x={p.x + 4} y={p.y + 4} fontSize={8} fill="#006622" fontFamily="monospace">{p.pin}</text>
      ))}
    </>
  );
}

function routeWire(x0: number, y0: number, x1: number, y1: number): string {
  if (Math.abs(y0 - y1) < 4) return `M ${x0} ${y0} L ${x1} ${y1}`;
  const mx = (x0 + x1) / 2;
  return `M ${x0} ${y0} C ${mx} ${y0} ${mx} ${y1} ${x1} ${y1}`;
}

export default function FBDCanvas({ program }: { program: ProgramDef }) {
  const layout = useMemo(() => {
    const inPins: Record<string, string[]> = {};
    const outPins: Record<string, string[]> = {};
    const pinConn: Record<string, Record<string, string>> = {};
    for (const b of program.blocks_used) { inPins[b.id] = []; outPins[b.id] = []; pinConn[b.id] = {}; }
    const flow = program.dependency_context?.flow;
    if (Array.isArray(flow)) {
      for (const f of flow) {
        const bid = f.block;
        if (!inPins[bid]) continue;
        if (f.usage === 'Input' || f.usage === 'Const') {
          if (!inPins[bid].includes(f.pin)) inPins[bid].push(f.pin);
        } else if (f.usage === 'Output') {
          if (!outPins[bid].includes(f.pin)) outPins[bid].push(f.pin);
        }
        if (f.connection) { pinConn[bid][f.pin] = f.connection; }
      }
    }
    for (const w of program.wires || []) {
      if (outPins[w.from_block] && !outPins[w.from_block].includes(w.from_pin)) outPins[w.from_block].push(w.from_pin);
      if (inPins[w.to_block] && !inPins[w.to_block].includes(w.to_pin)) inPins[w.to_block].push(w.to_pin);
    }
    for (const v of program.var_inputs || []) {
      if (inPins[v.to_block] && !inPins[v.to_block].includes(v.to_pin)) inPins[v.to_block].push(v.to_pin);
    }

    const geos: Record<string, { geo: any; shape: Shape; col: any }> = {};
    const initPos: Record<string, { x: number; y: number }> = {};
    for (const b of program.blocks_used) {
      const shape = getShape(b.block);
      geos[b.id] = {
        shape,
        geo: shapeGeometry(shape, inPins[b.id] || [], outPins[b.id] || []),
        col: CAT_COLOR[b.category || ''] || DEF_COLOR,
      };
      initPos[b.id] = { x: BLOCK_OFFSET_X + b.col * COL_W, y: b.row * ROW_H + 20 };
    }

    const varMap = new Map<string, { x: number; y: number; name: string; type: string; value: string }>();
    let vi = 0;
    for (const v of program.var_inputs || []) {
      if (!varMap.has(v.name)) {
        varMap.set(v.name, { x: VAR_X, y: vi * 70 + 20, name: v.name, type: v.type, value: v.value });
        vi++;
      }
    }

    const maxCol = Math.max(...program.blocks_used.map((b) => b.col), 0);
    const maxRow = Math.max(...program.blocks_used.map((b) => b.row), 0);
    const W = BLOCK_OFFSET_X + (maxCol + 1) * COL_W + 200;
    const H = Math.max((maxRow + 1) * ROW_H + 80, vi * 70 + 80);

    return { inPins, outPins, geos, initPos, varMap, pinConn, W, H };
  }, [program]);

  type PosMap = Record<string, { x: number; y: number }>;
  const [positions, setPositions] = useState<PosMap>({});
  useEffect(() => { setPositions(layout.initPos); }, [layout.initPos]);

  const [tooltip, setTooltip] = useState<{
    x: number; y: number; block: string; purpose: string;
  } | null>(null);

  const dragging = useRef<{
    id: string; startMx: number; startMy: number; startBx: number; startBy: number;
  } | null>(null);

  const onBlockMouseDown = useCallback(
    (e: React.MouseEvent, id: string) => {
      e.stopPropagation();
      const pos = positions[id] || { x: 0, y: 0 };
      dragging.current = { id, startMx: e.clientX, startMy: e.clientY, startBx: pos.x, startBy: pos.y };
    }, [positions]
  );

  const onSvgMouseMove = useCallback((e: React.MouseEvent<SVGSVGElement>) => {
    if (!dragging.current) return;
    const { id, startMx, startMy, startBx, startBy } = dragging.current;
    setPositions((prev) => ({ ...prev, [id]: { x: startBx + e.clientX - startMx, y: startBy + e.clientY - startMy } }));
  }, []);

  const onSvgMouseUp = useCallback(() => { dragging.current = null; }, []);

  const onBlockMouseEnter = useCallback(
    (e: React.MouseEvent, b: { block: string; purpose: string }) => {
      if (dragging.current) return;
      setTooltip({ x: e.clientX, y: e.clientY, block: b.block, purpose: b.purpose });
    }, []
  );

  const onBlockMouseLeave = useCallback(() => setTooltip(null), []);

  function portXY(blockId: string, pin: string, side: 'in' | 'out') {
    const pos = positions[blockId];
    const g = layout.geos[blockId];
    if (!pos || !g) return { x: 0, y: 0 };
    const ports = side === 'in' ? g.geo.inPorts : g.geo.outPorts;
    const found = ports.find((pp: any) => pp.pin === pin);
    if (!found) return { x: pos.x + (side === 'in' ? 0 : g.geo.w), y: pos.y + g.geo.h / 2 };
    return { x: pos.x + found.x, y: pos.y + found.y };
  }

  const { geos, varMap, pinConn, W, H } = layout;

  return (
    <div style={{ width: '100%', height: '100%', overflow: 'auto', background: '#0f1117', borderRadius: 8, position: 'relative' }}>
      {tooltip && (
        <div style={{ position: 'fixed', left: tooltip.x + 12, top: tooltip.y - 10, background: '#1e2a3a', border: '1px solid #4a9eff', borderRadius: 6, padding: '6px 10px', maxWidth: 260, zIndex: 999, pointerEvents: 'none', fontSize: 12, color: '#e0e8ff', fontFamily: 'monospace', lineHeight: 1.5, boxShadow: '0 4px 12px rgba(0,0,0,0.5)' }}>
          <div style={{ fontWeight: 'bold', color: '#4a9eff', marginBottom: 3 }}>{tooltip.block}</div>
          <div>{tooltip.purpose}</div>
        </div>
      )}

      <svg width={W} height={H} style={{ display: 'block' }} onMouseMove={onSvgMouseMove} onMouseUp={onSvgMouseUp} onMouseLeave={onSvgMouseUp}>
        <defs>
          <marker id="arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0,0 L0,6 L8,3 z" fill="#5588cc" /></marker>
          <marker id="arrow-var" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0,0 L0,6 L8,3 z" fill="#ccaa44" /></marker>
        </defs>

        {Array.from(varMap.values()).map((v) => (
          <g key={v.name} transform={`translate(${v.x},${v.y})`}>
            <rect x={0} y={0} width={130} height={50} rx={4} fill="#2a2a1a" stroke="#aaa88a" strokeWidth={1.5} strokeDasharray="5 3" />
            <text x={65} y={18} textAnchor="middle" fontSize={11} fontWeight="bold" fill="#ffe066" fontFamily="monospace">{v.name}</text>
            <text x={65} y={34} textAnchor="middle" fontSize={9} fill="#aaa" fontFamily="monospace">[{v.type}]={v.value}</text>
            <circle cx={130} cy={25} r={4} fill="#ccaa44" />
          </g>
        ))}

        {program.blocks_used.map((b) => {
          const pos = positions[b.id];
          if (!pos) return null;
          const { geo, shape, col } = geos[b.id];
          return (
            <g key={b.id} transform={`translate(${pos.x},${pos.y})`} style={{ cursor: 'grab' }}
              onMouseDown={(e) => onBlockMouseDown(e, b.id)}
              onMouseEnter={(e) => onBlockMouseEnter(e, b)}
              onMouseLeave={onBlockMouseLeave}>
              {renderShape(shape, geo, b.block, b.label || b.block, col, b.eqn)}
              {renderPinLabels(shape, geo, col)}
              {geo.inPorts.map((p: any) => (<circle key={`id_${p.pin}`} cx={p.x} cy={p.y} r={4} fill="#cc2200" />))}
              {geo.outPorts.map((p: any) => (<circle key={`od_${p.pin}`} cx={p.x} cy={p.y} r={4} fill="#006622" />))}
              <text x={geo.w / 2} y={geo.h + 14} textAnchor="middle" fontSize={8} fill="#888" fontFamily="monospace">{b.purpose}</text>
            </g>
          );
        })}

        {(program.wires || []).map((w, i) => {
          const src = portXY(w.from_block, w.from_pin, 'out');
          const dst = portXY(w.to_block, w.to_pin, 'in');
          const mid = { x: (src.x + dst.x) / 2, y: (src.y + dst.y) / 2 };
          return (
            <g key={`w${i}`}>
              <path d={routeWire(src.x, src.y, dst.x, dst.y)} fill="none" stroke="#5588cc" strokeWidth={2} markerEnd="url(#arrow)" />
              <text x={mid.x} y={mid.y - 4} textAnchor="middle" fontSize={8} fill="#7aaaee" fontFamily="monospace">{w.from_pin}\u2192{w.to_pin}</text>
            </g>
          );
        })}

        {(program.var_inputs || []).map((v, i) => {
          const varNode = varMap.get(v.name);
          if (!varNode) return null;
          const src = { x: varNode.x + 130, y: varNode.y + 25 };
          const dst = portXY(v.to_block, v.to_pin, 'in');
          return (
            <g key={`vw${i}`}>
              <path d={routeWire(src.x, src.y, dst.x, dst.y)} fill="none" stroke="#ccaa44" strokeWidth={1.5} strokeDasharray="6 3" markerEnd="url(#arrow-var)" />
              <text x={(src.x + dst.x) / 2} y={(src.y + dst.y) / 2 - 4} textAnchor="middle" fontSize={8} fill="#ccaa44" fontFamily="monospace">{v.to_pin}</text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
