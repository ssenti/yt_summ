import { useEffect } from 'react';

interface UseKeyboardShortcutProps {
  key: string;
  callback: () => void;
  metaKey?: boolean;
  shiftKey?: boolean;
}

export function useKeyboardShortcut({
  key,
  callback,
  metaKey = true,
  shiftKey = false,
}: UseKeyboardShortcutProps) {
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (
        event.key.toLowerCase() === key.toLowerCase() &&
        event.metaKey === metaKey &&
        event.shiftKey === shiftKey
      ) {
        event.preventDefault();
        callback();
      }
    };

    window.addEventListener('keydown', handleKeyDown);

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [key, callback, metaKey, shiftKey]);
}

