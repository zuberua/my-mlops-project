import { useState, useCallback } from 'react';
import { Message, ProgramDef } from './types';

const API = process.env.REACT_APP_API_URL || 'http://localhost:8001';

export function useChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [program, setProgram] = useState<ProgramDef | null>(null);

  const sendMessage = useCallback(
    async (text: string, sessionOption: string, sessionId: string) => {
      if (!text.trim()) return;

      const userMsg: Message = { role: 'user', content: text };
      setMessages((prev) => [...prev, userMsg]);
      setLoading(true);

      try {
        const res = await fetch(`${API}/chat`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            message: text,
            session_id: sessionId,
            enhancement_option: sessionOption,
          }),
        });

        if (!res.ok) {
          throw new Error(`Server error: ${res.status}`);
        }

        const data = await res.json();
        const raw = data.response || '';

        // Try to parse JSON program from the response
        let parsed: ProgramDef | undefined;
        try {
          // Try ```json ... ``` fenced block first
          const jsonMatch = raw.match(/```json\s*([\s\S]*?)```/);
          if (jsonMatch) {
            parsed = JSON.parse(jsonMatch[1]);
          } else {
            // Try finding a JSON object with blocks_used anywhere in the text
            const braceMatch = raw.match(/\{[\s\S]*"blocks_used"[\s\S]*\}/);
            if (braceMatch) {
              parsed = JSON.parse(braceMatch[0]);
            } else {
              // Try parsing the whole response as JSON
              const obj = JSON.parse(raw);
              if (obj.blocks_used) parsed = obj;
            }
          }
        } catch {
          // Not JSON, that's fine
        }

        if (parsed?.blocks_used) {
          setProgram(parsed);
        }

        const assistantMsg: Message = {
          role: 'assistant',
          content: raw,
          parsed,
          dynamodb_error: data.dynamodb_error || undefined,
        };
        setMessages((prev) => [...prev, assistantMsg]);
      } catch (err) {
        const errMsg: Message = {
          role: 'assistant',
          content: `Error: ${err instanceof Error ? err.message : 'Unknown error'}`,
        };
        setMessages((prev) => [...prev, errMsg]);
      } finally {
        setLoading(false);
      }
    },
    []
  );

  return { messages, loading, program, sendMessage };
}
