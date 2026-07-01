import { handleUpload } from '@vercel/blob/client';
import crypto from 'node:crypto';

function isValidUploadToken(token) {
  if (!token || typeof token !== 'string') {
    return false;
  }

  const [expiresAt, signature] = token.split('.');

  if (!expiresAt || !signature) {
    return false;
  }

  const expectedSignature = crypto
    .createHmac('sha256', process.env.SECRET_KEY)
    .update(expiresAt)
    .digest('hex');

  const expectedBuffer = Buffer.from(expectedSignature, 'utf8');
  const signatureBuffer = Buffer.from(signature, 'utf8');

  if (expectedBuffer.length !== signatureBuffer.length) {
    return false;
  }

  if (!crypto.timingSafeEqual(expectedBuffer, signatureBuffer)) {
    return false;
  }

  return Date.now() < Number(expiresAt) * 1000;
}

export default async function handler(request) {
  const body = await request.json();

  try {
    const jsonResponse = await handleUpload({
      body,
      request,
      onBeforeGenerateToken: async (pathname, clientPayload) => {
        if (!isValidUploadToken(clientPayload)) {
          throw new Error('Not authorized to upload.');
        }

        return {
          allowedContentTypes: [
            'video/mp4',
            'video/webm',
            'video/quicktime'
          ],
          addRandomSuffix: true
        };
      },
      onUploadCompleted: async () => {
        // No-op: the browser receives the blob URL directly and submits
        // it back to the Flask app as part of the product form.
      }
    });

    return Response.json(jsonResponse);
  } catch (error) {
    return Response.json({ error: error.message }, { status: 400 });
  }
}
