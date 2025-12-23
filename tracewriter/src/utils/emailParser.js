/**
 * Format date for display (e.g., "Dec 12, 2:34 PM")
 */
function formatDateDisplay(dateStr) {
  if (!dateStr) return 'Unknown date';
  try {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
    }) + ', ' + date.toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    });
  } catch {
    return dateStr;
  }
}

/**
 * Parse preprocessed JSON (from Python script) into internal format
 * The JSON is already in the right shape, just needs dateDisplay if missing
 */
export function parsePreprocessedJson(data) {
  const threads = Array.isArray(data) ? data : [data];

  return threads.map(thread => ({
    id: thread.id,
    subject: thread.subject,
    emails: thread.emails.map((email, index) => ({
      id: email.id || `msg_${index}`,
      from: email.from,
      to: email.to,
      date: email.date,
      dateDisplay: email.dateDisplay || formatDateDisplay(email.date),
      body: email.body,
    })),
  }));
}

/**
 * Check if imported JSON has pre-existing annotations
 */
export function hasExistingAnnotations(data) {
  const threads = Array.isArray(data) ? data : [data];
  return threads.some(thread =>
    thread.emails?.some(email => '_annotation_after' in email) ||
    thread.messages?.some(msg => '_annotation_after' in msg)
  );
}

/**
 * Parse pre-annotated JSON format (our export format)
 */
export function parseAnnotatedExport(data) {
  const threads = Array.isArray(data) ? data : [data];

  const parsedThreads = [];
  const annotations = {};

  for (const thread of threads) {
    // Handle both 'emails' (preprocessed) and 'messages' (exported) formats
    const messages = thread.emails || thread.messages || [];

    const emails = messages.map((msg, index) => {
      // Extract annotation if present
      if (msg._annotation_after) {
        annotations[`${thread.id}:${index}`] = msg._annotation_after;
      }

      return {
        id: msg.id,
        from: msg.from,
        to: msg.to,
        date: msg.date,
        dateDisplay: msg.dateDisplay || formatDateDisplay(msg.date),
        body: msg.body,
      };
    });

    parsedThreads.push({
      id: thread.id,
      subject: thread.subject,
      emails,
    });
  }

  return { threads: parsedThreads, annotations };
}

export default {
  parsePreprocessedJson,
  parseAnnotatedExport,
  hasExistingAnnotations,
};
