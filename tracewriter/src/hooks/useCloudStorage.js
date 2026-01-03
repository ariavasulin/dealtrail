import { useEffect, useCallback, useRef } from 'react';

/**
 * Debounce helper
 */
function debounce(fn, delay) {
  let timeoutId;
  return (...args) => {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => fn(...args), delay);
  };
}

/**
 * Hook to manage cloud persistence for TraceWriter
 */
export function useCloudStorage({
  properties,
  setProperties,
  annotations,
  setAnnotations,
  setCurrentPropertyIndex,
  setCurrentThreadIndex,
  setCurrentEmailIndex,
  setExpandedProperties,
}) {
  const isInitialized = useRef(false);
  const isSaving = useRef(false);

  // Load state from API on mount
  useEffect(() => {
    if (isInitialized.current) return;
    isInitialized.current = true;

    async function loadState() {
      try {
        const response = await fetch('/api/state');
        if (!response.ok) throw new Error('Failed to load state');

        const state = await response.json();

        if (state.properties?.length > 0) {
          setProperties(state.properties);
          setAnnotations(state.annotations || {});
          setCurrentPropertyIndex(0);
          setCurrentThreadIndex(0);
          setCurrentEmailIndex(0);
          // Expand first property
          setExpandedProperties(new Set([state.properties[0]?.id]));
          console.log('Loaded state from cloud:', {
            properties: state.properties.length,
            annotations: Object.keys(state.annotations || {}).length,
          });
        }
      } catch (error) {
        console.warn('Failed to load state from cloud:', error);
      }
    }

    loadState();
  }, [setProperties, setAnnotations, setCurrentPropertyIndex, setCurrentThreadIndex, setCurrentEmailIndex, setExpandedProperties]);

  // Save state to API
  const saveState = useCallback(async (props, anns) => {
    if (isSaving.current) return;
    if (!props?.length) return;

    isSaving.current = true;
    try {
      const response = await fetch('/api/state', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ properties: props, annotations: anns }),
      });

      if (!response.ok) throw new Error('Failed to save state');

      const result = await response.json();
      console.log('Saved state to cloud:', result.savedAt);
    } catch (error) {
      console.error('Failed to save state to cloud:', error);
    } finally {
      isSaving.current = false;
    }
  }, []);

  // Debounced save (2 seconds)
  const debouncedSave = useCallback(
    debounce((props, anns) => saveState(props, anns), 2000),
    [saveState]
  );

  // Auto-save when annotations change
  useEffect(() => {
    if (properties.length > 0) {
      debouncedSave(properties, annotations);
    }
  }, [annotations, properties, debouncedSave]);

  // Return manual save function for import
  return { saveState };
}
