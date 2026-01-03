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
 * New format: array of properties, each containing threads with emails
 */
export function parsePreprocessedJson(data) {
  const properties = Array.isArray(data) ? data : [data];

  return properties.map(property => ({
    id: property.id,
    subject: property.subject,
    property: property.property,
    threadCount: property.thread_count,
    emailCount: property.email_count,
    threads: property.threads.map(thread => ({
      id: thread.id,
      subject: thread.subject,
      normalizedSubject: thread.normalized_subject,
      emailCount: thread.email_count,
      emails: thread.emails.map((email, index) => ({
        id: email.id || `msg_${index}`,
        from: email.from,
        to: email.to,
        date: email.date,
        dateDisplay: email.dateDisplay || formatDateDisplay(email.date),
        subject: email.subject,
        body: email.body,
      })),
    })),
  }));
}

/**
 * Check if imported JSON has pre-existing annotations
 */
export function hasExistingAnnotations(data) {
  const items = Array.isArray(data) ? data : [data];

  // Check if it's the new property-based format
  if (items[0]?.threads) {
    return items.some(property =>
      property.threads?.some(thread =>
        thread.emails?.some(email => '_annotation_after' in email)
      )
    );
  }

  // Legacy flat thread format
  return items.some(thread =>
    thread.emails?.some(email => '_annotation_after' in email) ||
    thread.messages?.some(msg => '_annotation_after' in msg)
  );
}

/**
 * Parse pre-annotated JSON format (our export format)
 */
export function parseAnnotatedExport(data) {
  const items = Array.isArray(data) ? data : [data];
  const annotations = {};

  // Check if it's the new property-based format
  if (items[0]?.threads) {
    const properties = items.map(property => ({
      id: property.id,
      subject: property.subject,
      property: property.property,
      threadCount: property.thread_count || property.threadCount,
      emailCount: property.email_count || property.emailCount,
      threads: property.threads.map(thread => {
        const emails = thread.emails.map((email, index) => {
          if (email._annotation_after) {
            annotations[`${thread.id}:${index}`] = email._annotation_after;
          }
          return {
            id: email.id,
            from: email.from,
            to: email.to,
            date: email.date,
            dateDisplay: email.dateDisplay || formatDateDisplay(email.date),
            subject: email.subject,
            body: email.body,
          };
        });
        return {
          id: thread.id,
          subject: thread.subject,
          normalizedSubject: thread.normalized_subject || thread.normalizedSubject,
          emailCount: thread.email_count || thread.emailCount,
          emails,
        };
      }),
    }));
    return { properties, annotations };
  }

  // Legacy flat thread format - return as single property
  const parsedThreads = [];
  for (const thread of items) {
    const messages = thread.emails || thread.messages || [];
    const emails = messages.map((msg, index) => {
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
    parsedThreads.push({ id: thread.id, subject: thread.subject, emails });
  }

  // Wrap legacy format in a single property
  const properties = [{
    id: 'legacy_import',
    subject: 'Imported Threads',
    property: 'imported',
    threadCount: parsedThreads.length,
    emailCount: parsedThreads.reduce((sum, t) => sum + t.emails.length, 0),
    threads: parsedThreads,
  }];

  return { properties, annotations };
}

export default {
  parsePreprocessedJson,
  parseAnnotatedExport,
  hasExistingAnnotations,
};
