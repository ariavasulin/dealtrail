/**
 * Generate annotated export JSON with _annotation_after fields
 */
export function generateExport(properties, annotations, annotator = 'team') {
  return properties.map(property => ({
    id: property.id,
    subject: property.subject,
    property: property.property,
    thread_count: property.threadCount,
    email_count: property.emailCount,
    threads: property.threads.map(thread => ({
      id: thread.id,
      subject: thread.subject,
      normalized_subject: thread.normalizedSubject,
      email_count: thread.emailCount,
      emails: thread.emails.map((email, index) => {
        const annotationKey = `${thread.id}:${index}`;
        const annotation = annotations[annotationKey]?.trim() || null;
        const isLastEmail = index === thread.emails.length - 1;

        return {
          id: email.id,
          from: email.from,
          to: email.to,
          date: email.date,
          dateDisplay: email.dateDisplay,
          subject: email.subject,
          body: email.body,
          _annotation_after: isLastEmail ? null : annotation,
        };
      }),
    })),
    _metadata: {
      annotated_at: new Date().toISOString(),
      annotator,
    },
  }));
}

/**
 * Download JSON as file
 */
export function downloadJson(data, filename = 'annotated-threads.json') {
  const json = JSON.stringify(data, null, 2);
  const blob = new Blob([json], { type: 'application/json' });
  const url = URL.createObjectURL(blob);

  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
