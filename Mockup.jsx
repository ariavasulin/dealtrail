import React, { useState } from 'react';

// Mock data to simulate Gmail threads
const mockThreads = [
  {
    id: 'thread_1',
    subject: '123 Oak Street - Disclosure Documents',
    emails: [
      { id: 1, from: 'buyer@email.com', date: 'Dec 12, 2:34 PM', body: 'Hi Matan, we reviewed the inspection report and have some concerns about the roof. Can you send over the seller\'s disclosure?' },
      { id: 2, from: 'matan@theagency.com', date: 'Dec 12, 3:15 PM', body: 'Of course! I\'ll get that over to you right away. The seller completed it last week.' },
      { id: 3, from: 'matan@theagency.com', date: 'Dec 12, 3:45 PM', body: 'Here\'s the signed disclosure. Let me know if you have any questions about the roof - the seller did have it inspected 2 years ago.' },
      { id: 4, from: 'buyer@email.com', date: 'Dec 12, 5:02 PM', body: 'Thanks! Can we get a copy of that roof inspection report as well?' },
    ]
  },
  {
    id: 'thread_2', 
    subject: '456 Maple Ave - Escrow Timeline',
    emails: [
      { id: 1, from: 'title@titleco.com', date: 'Dec 11, 10:00 AM', body: 'We need the amended purchase agreement to proceed with escrow. Current close date is Dec 28.' },
      { id: 2, from: 'matan@theagency.com', date: 'Dec 11, 11:30 AM', body: 'Understood. I\'ll coordinate with both parties and get that to you by EOD tomorrow.' },
      { id: 3, from: 'matan@theagency.com', date: 'Dec 13, 9:15 AM', body: 'Attached is the fully executed amendment. New close date is Jan 5. Please confirm receipt.' },
    ]
  },
  {
    id: 'thread_3',
    subject: '789 Pine Rd - Inspection Scheduling', 
    emails: [
      { id: 1, from: 'selleragent@realty.com', date: 'Dec 10, 4:00 PM', body: 'Buyer wants to schedule inspection for this week. What times work for access?' },
      { id: 2, from: 'matan@theagency.com', date: 'Dec 10, 4:30 PM', body: 'Let me check with the sellers and get back to you within the hour.' },
    ]
  }
];

export default function EmailAnnotator() {
  const [currentThreadIndex, setCurrentThreadIndex] = useState(0);
  const [currentEmailIndex, setCurrentEmailIndex] = useState(0);
  const [annotations, setAnnotations] = useState({});
  const [focusedAnnotation, setFocusedAnnotation] = useState(null);

  const currentThread = mockThreads[currentThreadIndex];
  const totalThreads = mockThreads.length;
  const totalEmails = currentThread.emails.length;

  // Get annotation key for a gap
  const getAnnotationKey = (threadId, afterEmailIndex) => `${threadId}:${afterEmailIndex}`;

  // Handle keyboard navigation
  React.useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.altKey && (e.key === 'j' || e.key === 'ArrowDown')) {
        e.preventDefault();
        if (currentEmailIndex < totalEmails - 1) {
          setCurrentEmailIndex(i => i + 1);
          setFocusedAnnotation(null);
        }
      } else if (e.altKey && (e.key === 'k' || e.key === 'ArrowUp')) {
        e.preventDefault();
        if (currentEmailIndex > 0) {
          setCurrentEmailIndex(i => i - 1);
          setFocusedAnnotation(null);
        }
      } else if (e.altKey && e.key === 'n') {
        e.preventDefault();
        if (currentThreadIndex < totalThreads - 1) {
          setCurrentThreadIndex(i => i + 1);
          setCurrentEmailIndex(0);
          setFocusedAnnotation(null);
        }
      } else if (e.altKey && e.key === 'p') {
        e.preventDefault();
        if (currentThreadIndex > 0) {
          setCurrentThreadIndex(i => i - 1);
          setCurrentEmailIndex(0);
          setFocusedAnnotation(null);
        }
      } else if (e.key === 'Enter' && !focusedAnnotation && !e.shiftKey) {
        e.preventDefault();
        setFocusedAnnotation(getAnnotationKey(currentThread.id, currentEmailIndex));
      } else if (e.key === 'Escape') {
        setFocusedAnnotation(null);
        document.activeElement.blur();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [currentEmailIndex, currentThreadIndex, totalEmails, totalThreads, focusedAnnotation, currentThread.id]);

  // Auto-focus annotation input when focused
  React.useEffect(() => {
    if (focusedAnnotation) {
      const input = document.getElementById(`annotation-${focusedAnnotation}`);
      if (input) input.focus();
    }
  }, [focusedAnnotation]);

  const handleAnnotationChange = (key, value) => {
    setAnnotations(prev => ({ ...prev, [key]: value }));
  };

  const getAnnotatedCount = () => {
    return Object.keys(annotations).filter(k => k.startsWith(currentThread.id) && annotations[k]?.trim()).length;
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
          <span style={{ color: '#8a8480' }}>threads</span>
          <span style={{ color: '#4a4745' }}>›</span>
          <span style={{ color: '#c9a86c' }}>{currentThread.subject}</span>
        </div>
        <div style={{ color: '#5a5755', fontSize: '12px' }}>
          {currentThreadIndex + 1}/{totalThreads} threads · {getAnnotatedCount()}/{totalEmails - 1} annotated
        </div>
      </div>

      <div style={{ display: 'flex', height: 'calc(100vh - 100px)' }}>
        {/* Thread list sidebar */}
        <div style={{
          width: '280px',
          borderRight: '1px solid #2a2725',
          padding: '12px 0',
          overflowY: 'auto'
        }}>
          {mockThreads.map((thread, idx) => (
            <div
              key={thread.id}
              onClick={() => { setCurrentThreadIndex(idx); setCurrentEmailIndex(0); }}
              style={{
                padding: '10px 16px',
                cursor: 'pointer',
                backgroundColor: idx === currentThreadIndex ? '#252220' : 'transparent',
                borderLeft: idx === currentThreadIndex ? '2px solid #c9a86c' : '2px solid transparent',
              }}
            >
              <div style={{ 
                color: idx === currentThreadIndex ? '#e8e4df' : '#8a8480',
                marginBottom: '4px',
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis'
              }}>
                {thread.subject}
              </div>
              <div style={{ color: '#5a5755', fontSize: '11px' }}>
                {thread.emails.length} emails
              </div>
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
                  <span style={{ color: '#5a5755', fontSize: '12px' }}>{email.date}</span>
                </div>
                <div style={{ color: '#c5c1bc' }}>
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
        <div style={{ display: 'flex', gap: '24px' }}>
          <span style={{ color: '#5a5755' }}>
            <span style={{ color: '#8a8480', backgroundColor: '#252220', padding: '2px 6px', borderRadius: '3px', marginRight: '6px' }}>Alt+j/k</span>
            navigate emails
          </span>
          <span style={{ color: '#5a5755' }}>
            <span style={{ color: '#8a8480', backgroundColor: '#252220', padding: '2px 6px', borderRadius: '3px', marginRight: '6px' }}>Alt+n/p</span>
            next/prev thread
          </span>
          <span style={{ color: '#5a5755' }}>
            <span style={{ color: '#8a8480', backgroundColor: '#252220', padding: '2px 6px', borderRadius: '3px', marginRight: '6px' }}>Enter</span>
            annotate
          </span>
          <span style={{ color: '#5a5755' }}>
            <span style={{ color: '#8a8480', backgroundColor: '#252220', padding: '2px 6px', borderRadius: '3px', marginRight: '6px' }}>Esc</span>
            done
          </span>
        </div>
        <div style={{ color: '#5a5755', fontSize: '12px' }}>
          <span style={{ color: '#c9a86c' }}>TRACEWRITER</span>
          <span style={{ marginLeft: '12px' }}>email {currentEmailIndex + 1}/{totalEmails}</span>
        </div>
      </div>
    </div>
  );
}
