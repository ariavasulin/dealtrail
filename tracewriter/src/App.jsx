import React, { useState, useEffect } from 'react';
import './index.css';
import { parsePreprocessedJson, parseAnnotatedExport, hasExistingAnnotations } from './utils/emailParser';
import { generateExport, downloadJson } from './utils/exportAnnotations';
import { useCloudStorage } from './hooks/useCloudStorage';

// Create mock data in new format
const mockProperties = [
  {
    id: 'prop_mock',
    subject: 'Sample Property',
    property: 'sample property',
    threadCount: 2,
    emailCount: 5,
    threads: [
      {
        id: 'prop_mock_thread_0',
        subject: '123 Oak Street - Disclosure Documents',
        emailCount: 4,
        emails: [
          { id: 1, from: 'buyer@email.com', dateDisplay: 'Dec 12, 2:34 PM', body: 'Hi Matan, we reviewed the inspection report and have some concerns about the roof.' },
          { id: 2, from: 'matan@theagency.com', dateDisplay: 'Dec 12, 3:15 PM', body: 'Of course! I\'ll get that over to you right away.' },
          { id: 3, from: 'matan@theagency.com', dateDisplay: 'Dec 12, 3:45 PM', body: 'Here\'s the signed disclosure. Let me know if you have any questions.' },
          { id: 4, from: 'buyer@email.com', dateDisplay: 'Dec 12, 5:02 PM', body: 'Thanks! Can we get a copy of that roof inspection report as well?' },
        ]
      },
      {
        id: 'prop_mock_thread_1',
        subject: '123 Oak Street - Escrow Timeline',
        emailCount: 2,
        emails: [
          { id: 1, from: 'title@titleco.com', dateDisplay: 'Dec 11, 10:00 AM', body: 'We need the amended purchase agreement to proceed with escrow.' },
          { id: 2, from: 'matan@theagency.com', dateDisplay: 'Dec 11, 11:30 AM', body: 'Understood. I\'ll coordinate with both parties.' },
        ]
      }
    ]
  }
];

export default function App() {
  const [properties, setProperties] = useState(mockProperties);
  const [currentPropertyIndex, setCurrentPropertyIndex] = useState(0);
  const [currentThreadIndex, setCurrentThreadIndex] = useState(0);
  const [currentEmailIndex, setCurrentEmailIndex] = useState(0);
  const [annotations, setAnnotations] = useState({});
  const [focusedAnnotation, setFocusedAnnotation] = useState(null);
  const [expandedProperties, setExpandedProperties] = useState(new Set([mockProperties[0]?.id]));

  // Cloud storage for persistence
  const { saveState } = useCloudStorage({
    properties,
    setProperties,
    annotations,
    setAnnotations,
    setCurrentPropertyIndex,
    setCurrentThreadIndex,
    setCurrentEmailIndex,
    setExpandedProperties,
  });

  const currentProperty = properties[currentPropertyIndex] || { subject: 'No properties', threads: [] };
  const currentThread = currentProperty.threads[currentThreadIndex] || { subject: 'No threads', emails: [] };
  const totalProperties = properties.length;
  const totalThreads = currentProperty.threads.length;
  const totalEmails = currentThread.emails.length;

  // Get annotation key for a gap
  const getAnnotationKey = (threadId, afterEmailIndex) => `${threadId}:${afterEmailIndex}`;

  // Handle keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e) => {
      const inEditMode = focusedAnnotation !== null;

      if (e.key === 'Tab') {
        e.preventDefault();
        if (e.shiftKey) {
          // Shift+Tab: previous email
          if (currentEmailIndex > 0) {
            const newIndex = currentEmailIndex - 1;
            setCurrentEmailIndex(newIndex);
            if (inEditMode) {
              setFocusedAnnotation(getAnnotationKey(currentThread.id, newIndex));
            }
          }
        } else {
          // Tab: next email
          if (currentEmailIndex < totalEmails - 1) {
            const newIndex = currentEmailIndex + 1;
            setCurrentEmailIndex(newIndex);
            if (inEditMode && newIndex < totalEmails - 1) {
              setFocusedAnnotation(getAnnotationKey(currentThread.id, newIndex));
            } else if (inEditMode) {
              setFocusedAnnotation(null);
            }
          }
        }
      } else if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
        e.preventDefault();

        if (e.metaKey && e.shiftKey) {
          // Cmd+Shift+Arrow: switch properties
          if (e.key === 'ArrowDown') {
            if (currentPropertyIndex < totalProperties - 1) {
              const nextProperty = properties[currentPropertyIndex + 1];
              setCurrentPropertyIndex(i => i + 1);
              setCurrentThreadIndex(0);
              setCurrentEmailIndex(0);
              setExpandedProperties(prev => new Set([...prev, nextProperty.id]));
              if (inEditMode && nextProperty.threads[0]?.emails.length > 1) {
                setFocusedAnnotation(getAnnotationKey(nextProperty.threads[0].id, 0));
              } else {
                setFocusedAnnotation(null);
              }
            }
          } else {
            if (currentPropertyIndex > 0) {
              const prevProperty = properties[currentPropertyIndex - 1];
              setCurrentPropertyIndex(i => i - 1);
              setCurrentThreadIndex(0);
              setCurrentEmailIndex(0);
              setExpandedProperties(prev => new Set([...prev, prevProperty.id]));
              if (inEditMode && prevProperty.threads[0]?.emails.length > 1) {
                setFocusedAnnotation(getAnnotationKey(prevProperty.threads[0].id, 0));
              } else {
                setFocusedAnnotation(null);
              }
            }
          }
        } else if (e.shiftKey) {
          // Shift+Arrow: switch threads within property
          if (e.key === 'ArrowDown') {
            if (currentThreadIndex < totalThreads - 1) {
              const nextThread = currentProperty.threads[currentThreadIndex + 1];
              setCurrentThreadIndex(i => i + 1);
              setCurrentEmailIndex(0);
              if (inEditMode && nextThread.emails.length > 1) {
                setFocusedAnnotation(getAnnotationKey(nextThread.id, 0));
              } else {
                setFocusedAnnotation(null);
              }
            }
          } else {
            if (currentThreadIndex > 0) {
              const prevThread = currentProperty.threads[currentThreadIndex - 1];
              setCurrentThreadIndex(i => i - 1);
              setCurrentEmailIndex(0);
              if (inEditMode && prevThread.emails.length > 1) {
                setFocusedAnnotation(getAnnotationKey(prevThread.id, 0));
              } else {
                setFocusedAnnotation(null);
              }
            }
          }
        } else {
          // Arrow without modifiers: navigate emails
          if (e.key === 'ArrowDown') {
            if (currentEmailIndex < totalEmails - 1) {
              const newIndex = currentEmailIndex + 1;
              setCurrentEmailIndex(newIndex);
              if (inEditMode && newIndex < totalEmails - 1) {
                setFocusedAnnotation(getAnnotationKey(currentThread.id, newIndex));
              } else if (inEditMode) {
                setFocusedAnnotation(null);
              }
            }
          } else {
            if (currentEmailIndex > 0) {
              const newIndex = currentEmailIndex - 1;
              setCurrentEmailIndex(newIndex);
              if (inEditMode) {
                setFocusedAnnotation(getAnnotationKey(currentThread.id, newIndex));
              }
            }
          }
        }
      } else if (e.key === 'Enter' && !inEditMode && !e.shiftKey) {
        e.preventDefault();
        if (currentEmailIndex < totalEmails - 1) {
          setFocusedAnnotation(getAnnotationKey(currentThread.id, currentEmailIndex));
        }
      } else if (e.key === 'Escape') {
        setFocusedAnnotation(null);
        document.activeElement.blur();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [currentEmailIndex, currentThreadIndex, currentPropertyIndex, totalEmails, totalThreads, totalProperties, currentThread.id, currentProperty, properties, focusedAnnotation]);

  // Auto-focus annotation input when focused
  useEffect(() => {
    if (focusedAnnotation) {
      const input = document.getElementById(`annotation-${focusedAnnotation}`);
      if (input) input.focus();
    }
  }, [focusedAnnotation]);

  const handleAnnotationChange = (key, value) => {
    setAnnotations(prev => ({ ...prev, [key]: value }));
  };

  // Handle JSON import (from preprocessed MBOX or annotated export)
  const handleImport = (json) => {
    let parsedProperties;
    if (hasExistingAnnotations(json)) {
      // Re-importing annotated export
      const { properties: parsed, annotations: existingAnnotations } = parseAnnotatedExport(json);
      parsedProperties = parsed;
      setProperties(parsed);
      setAnnotations(prev => ({ ...prev, ...existingAnnotations }));
      // Save immediately after import
      saveState(parsed, { ...annotations, ...existingAnnotations });
    } else {
      // Fresh preprocessed JSON from Python script
      parsedProperties = parsePreprocessedJson(json);
      setProperties(parsedProperties);
      // Save immediately after import
      saveState(parsedProperties, annotations);
    }
    setCurrentPropertyIndex(0);
    setCurrentThreadIndex(0);
    setCurrentEmailIndex(0);
    setFocusedAnnotation(null);
    // Expand first property by default
    if (parsedProperties.length > 0) {
      setExpandedProperties(new Set([parsedProperties[0]?.id]));
    }
  };

  const handleExport = () => {
    const exportData = generateExport(properties, annotations);
    const filename = `tracewriter-export-${new Date().toISOString().split('T')[0]}.json`;
    downloadJson(exportData, filename);
  };

  return (
    <div style={{
      backgroundColor: '#1a1816',
      minHeight: '100vh',
      color: '#e8e4df',
      fontFamily: '"SF Mono", "Fira Code", "Consolas", monospace',
      fontSize: '13px',
      lineHeight: '1.6'
    }}>
      {/* Header */}
      <div style={{
        borderBottom: '1px solid #2a2725',
        padding: '12px 20px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span style={{ color: '#8a8480' }}>properties</span>
          <span style={{ color: '#4a4745' }}>/</span>
          <span style={{ color: '#c9a86c' }}>{currentProperty.subject}</span>
          <span style={{ color: '#4a4745' }}>/</span>
          <span style={{
            color: '#8a8480',
            maxWidth: '400px',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap'
          }}>
            {currentThread.subject}
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <button
            onClick={() => document.getElementById('file-input').click()}
            style={{
              backgroundColor: '#252220',
              border: '1px solid #3a3735',
              borderRadius: '4px',
              color: '#c9a86c',
              padding: '6px 12px',
              cursor: 'pointer',
              fontFamily: 'inherit',
              fontSize: '12px',
            }}
          >
            Import JSON
          </button>
          <input
            id="file-input"
            type="file"
            accept=".json"
            style={{ display: 'none' }}
            onChange={(e) => {
              const file = e.target.files[0];
              if (file) {
                file.text().then(text => {
                  try {
                    const json = JSON.parse(text);
                    handleImport(json);
                  } catch (err) {
                    alert(`Failed to parse JSON: ${err.message}`);
                  }
                });
              }
              e.target.value = '';
            }}
          />
          {totalProperties > 0 && (
            <button
              onClick={handleExport}
              style={{
                backgroundColor: '#252220',
                border: '1px solid #3a3735',
                borderRadius: '4px',
                color: '#8a8480',
                padding: '6px 12px',
                cursor: 'pointer',
                fontFamily: 'inherit',
                fontSize: '12px',
              }}
            >
              Export
            </button>
          )}
        </div>
      </div>

      <div style={{ display: 'flex', height: 'calc(100vh - 100px)' }}>
        {/* Property/Thread list sidebar */}
        <div style={{
          width: '300px',
          borderRight: '1px solid #2a2725',
          padding: '12px 0',
          overflowY: 'auto'
        }}>
          {properties.map((property, propIdx) => (
            <div key={property.id}>
              {/* Property header */}
              <div
                onClick={() => {
                  setExpandedProperties(prev => {
                    const next = new Set(prev);
                    if (next.has(property.id)) {
                      next.delete(property.id);
                    } else {
                      next.add(property.id);
                    }
                    return next;
                  });
                  if (propIdx !== currentPropertyIndex) {
                    setCurrentPropertyIndex(propIdx);
                    setCurrentThreadIndex(0);
                    setCurrentEmailIndex(0);
                    setFocusedAnnotation(null);
                  }
                }}
                style={{
                  padding: '10px 16px',
                  cursor: 'pointer',
                  backgroundColor: propIdx === currentPropertyIndex ? '#252220' : 'transparent',
                  borderLeft: propIdx === currentPropertyIndex ? '2px solid #c9a86c' : '2px solid transparent',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                }}
              >
                <span style={{
                  color: '#5a5755',
                  fontSize: '10px',
                  width: '12px',
                }}>
                  {expandedProperties.has(property.id) ? '▼' : '▶'}
                </span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{
                    color: propIdx === currentPropertyIndex ? '#c9a86c' : '#e8e4df',
                    fontWeight: propIdx === currentPropertyIndex ? '500' : '400',
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis'
                  }}>
                    {property.subject}
                  </div>
                  <div style={{ color: '#5a5755', fontSize: '11px' }}>
                    {property.threadCount} threads · {property.emailCount} emails
                  </div>
                </div>
              </div>

              {/* Threads within property */}
              {expandedProperties.has(property.id) && (
                <div style={{ marginLeft: '20px' }}>
                  {property.threads.map((thread, threadIdx) => (
                    <div
                      key={thread.id}
                      onClick={() => {
                        setCurrentPropertyIndex(propIdx);
                        setCurrentThreadIndex(threadIdx);
                        setCurrentEmailIndex(0);
                        setFocusedAnnotation(null);
                      }}
                      style={{
                        padding: '8px 16px',
                        cursor: 'pointer',
                        backgroundColor: propIdx === currentPropertyIndex && threadIdx === currentThreadIndex ? '#1e1c1a' : 'transparent',
                        borderLeft: propIdx === currentPropertyIndex && threadIdx === currentThreadIndex ? '2px solid #7a9f6a' : '2px solid transparent',
                      }}
                    >
                      <div style={{
                        color: propIdx === currentPropertyIndex && threadIdx === currentThreadIndex ? '#e8e4df' : '#8a8480',
                        fontSize: '12px',
                        whiteSpace: 'nowrap',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis'
                      }}>
                        {thread.subject}
                      </div>
                      <div style={{ color: '#5a5755', fontSize: '10px' }}>
                        {thread.emailCount || thread.emails?.length || 0} emails
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Main content */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '20px 32px' }}>
          {currentThread.emails.map((email, idx) => (
            <React.Fragment key={email.id}>
              {/* Email */}
              <div style={{
                marginBottom: '8px',
                padding: '16px',
                backgroundColor: idx === currentEmailIndex ? '#252220' : 'transparent',
                borderRadius: '4px',
                border: idx === currentEmailIndex ? '1px solid #3a3735' : '1px solid transparent'
              }}>
                <div style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  marginBottom: '8px'
                }}>
                  <span style={{ color: '#c9a86c' }}>{email.from}</span>
                  <span style={{ color: '#5a5755', fontSize: '12px' }}>{email.dateDisplay}</span>
                </div>
                <div style={{ color: '#c5c1bc', whiteSpace: 'pre-wrap' }}>
                  {email.body}
                </div>
              </div>

              {/* Annotation gap (after each email except the last) */}
              {idx < currentThread.emails.length - 1 && (
                <div style={{
                  margin: '4px 0 16px 0',
                  padding: '0 16px'
                }}>
                  <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    marginBottom: '6px'
                  }}>
                    <div style={{
                      flex: 1,
                      height: '1px',
                      backgroundColor: '#2a2725'
                    }} />
                    <span style={{
                      color: annotations[getAnnotationKey(currentThread.id, idx)]?.trim() ? '#7a9f6a' : '#5a5755',
                      fontSize: '11px',
                      textTransform: 'uppercase',
                      letterSpacing: '0.5px'
                    }}>
                      {annotations[getAnnotationKey(currentThread.id, idx)]?.trim() ? '✓ annotated' : 'off-screen action'}
                    </span>
                    <div style={{
                      flex: 1,
                      height: '1px',
                      backgroundColor: '#2a2725'
                    }} />
                  </div>

                  {(idx === currentEmailIndex || annotations[getAnnotationKey(currentThread.id, idx)]) && (
                    <textarea
                      id={`annotation-${getAnnotationKey(currentThread.id, idx)}`}
                      value={annotations[getAnnotationKey(currentThread.id, idx)] || ''}
                      onChange={(e) => handleAnnotationChange(getAnnotationKey(currentThread.id, idx), e.target.value)}
                      onFocus={() => setFocusedAnnotation(getAnnotationKey(currentThread.id, idx))}
                      placeholder="what happened between these emails..."
                      style={{
                        width: '100%',
                        backgroundColor: '#1e1c1a',
                        border: focusedAnnotation === getAnnotationKey(currentThread.id, idx)
                          ? '1px solid #c9a86c'
                          : '1px solid #2a2725',
                        borderRadius: '4px',
                        color: '#e8e4df',
                        padding: '10px 12px',
                        fontFamily: 'inherit',
                        fontSize: '13px',
                        lineHeight: '1.5',
                        resize: 'none',
                        minHeight: '60px',
                        outline: 'none'
                      }}
                    />
                  )}
                </div>
              )}
            </React.Fragment>
          ))}
        </div>
      </div>

      {/* Footer / keyboard hints */}
      <div style={{
        position: 'fixed',
        bottom: 0,
        left: 0,
        right: 0,
        backgroundColor: '#1a1816',
        borderTop: '1px solid #2a2725',
        padding: '10px 20px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <div style={{ display: 'flex', gap: '20px', flexWrap: 'wrap' }}>
          <span style={{ color: '#5a5755' }}>
            <span style={{ color: '#8a8480', backgroundColor: '#252220', padding: '2px 6px', borderRadius: '3px', marginRight: '6px' }}>↑/↓</span>
            emails
          </span>
          <span style={{ color: '#5a5755' }}>
            <span style={{ color: '#8a8480', backgroundColor: '#252220', padding: '2px 6px', borderRadius: '3px', marginRight: '6px' }}>⇧↑/↓</span>
            threads
          </span>
          <span style={{ color: '#5a5755' }}>
            <span style={{ color: '#8a8480', backgroundColor: '#252220', padding: '2px 6px', borderRadius: '3px', marginRight: '6px' }}>⌘⇧↑/↓</span>
            properties
          </span>
          <span style={{ color: '#5a5755' }}>
            <span style={{ color: '#8a8480', backgroundColor: '#252220', padding: '2px 6px', borderRadius: '3px', marginRight: '6px' }}>Enter</span>
            edit
          </span>
          <span style={{ color: '#5a5755' }}>
            <span style={{ color: '#8a8480', backgroundColor: '#252220', padding: '2px 6px', borderRadius: '3px', marginRight: '6px' }}>Esc</span>
            view
          </span>
        </div>
        <div style={{ color: '#5a5755', fontSize: '12px' }}>
          <span style={{ color: '#c9a86c' }}>TRACEWRITER</span>
          <span style={{ marginLeft: '12px' }}>
            {currentPropertyIndex + 1}/{totalProperties} properties
            {' · '}
            {currentThreadIndex + 1}/{totalThreads} threads
            {' · '}
            email {currentEmailIndex + 1}/{totalEmails}
          </span>
        </div>
      </div>
    </div>
  );
}
