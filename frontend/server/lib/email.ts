/**
 * Email Service for OccultaShield
 * Sends notifications via Nodemailer using Gmail SMTP
 */
import nodemailer from 'nodemailer';
import type { Transporter } from 'nodemailer';
import { ENV } from './env';

// =============================================================================
// TRANSPORTER CONFIGURATION
// =============================================================================

let transporter: Transporter | null = null;

function getTransporter(): Transporter {
    if (!transporter) {
        transporter = nodemailer.createTransport({
            host: 'smtp.gmail.com',
            port: 465,
            secure: true,
            auth: {
                user: ENV.SMTP_USER,
                pass: ENV.SMTP_PASS,
            },
        });
    }
    return transporter;
}

// Email sender address
const FROM_ADDRESS = ENV.SMTP_FROM || `OccultaShield <${ENV.SMTP_USER}>`;

// =============================================================================
// EMAIL TEMPLATES
// =============================================================================

function getBaseTemplate(content: string, title: string): string {
    return `
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${title}</title>
</head>
<body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #0f0f1a;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width: 600px; margin: 0 auto; background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%); border-radius: 16px; overflow: hidden;">
    
    <!-- Header -->
    <tr>
      <td style="padding: 40px 40px 20px; text-align: center;">
        <div style="display: inline-block; background: linear-gradient(135deg, #6366f1, #8b5cf6); padding: 16px 24px; border-radius: 12px;">
          <span style="font-size: 24px; font-weight: 700; color: white; letter-spacing: -0.5px;">🛡️ OccultaShield</span>
        </div>
      </td>
    </tr>
    
    <!-- Content -->
    <tr>
      <td style="padding: 20px 40px 40px;">
        ${content}
      </td>
    </tr>
    
    <!-- Footer -->
    <tr>
      <td style="padding: 20px 40px; background: rgba(0,0,0,0.3); border-top: 1px solid rgba(255,255,255,0.1);">
        <p style="margin: 0; font-size: 12px; color: #9ca3af; text-align: center;">
          Este email fue enviado automáticamente por OccultaShield.<br>
          Si no solicitaste esta acción, puedes ignorar este mensaje.
        </p>
        <p style="margin: 10px 0 0; font-size: 12px; color: #6b7280; text-align: center;">
          © ${new Date().getFullYear()} OccultaShield - Privacy-First Video Protection
        </p>
      </td>
    </tr>
  </table>
</body>
</html>
  `.trim();
}

// =============================================================================
// EMAIL FUNCTIONS
// =============================================================================

/**
 * Send notification when a new user registers (pending approval)
 */
export async function sendPendingNotification(
    userEmail: string,
    userName: string
): Promise<boolean> {
    const content = `
    <h1 style="margin: 0 0 16px; font-size: 28px; font-weight: 700; color: #f9fafb;">
      ¡Bienvenido, ${userName}!
    </h1>
    <p style="margin: 0 0 24px; font-size: 16px; color: #d1d5db; line-height: 1.6;">
      Tu cuenta ha sido creada correctamente en OccultaShield.
    </p>
    
    <div style="background: rgba(251, 191, 36, 0.1); border: 1px solid rgba(251, 191, 36, 0.3); border-radius: 12px; padding: 20px; margin-bottom: 24px;">
      <div style="display: flex; align-items: center; gap: 12px;">
        <span style="font-size: 24px;">⏳</span>
        <div>
          <p style="margin: 0; font-weight: 600; color: #fbbf24; font-size: 16px;">
            Pendiente de Aprobación
          </p>
          <p style="margin: 4px 0 0; color: #d1d5db; font-size: 14px;">
            Un administrador revisará tu solicitud en 1-2 días laborables.
          </p>
        </div>
      </div>
    </div>
    
    <p style="margin: 0; font-size: 14px; color: #9ca3af; line-height: 1.6;">
      Recibirás otro email cuando tu cuenta sea activada y puedas comenzar a usar la plataforma.
    </p>
  `;

    try {
        await getTransporter().sendMail({
            from: FROM_ADDRESS,
            to: userEmail,
            subject: '🛡️ OccultaShield - Cuenta pendiente de aprobación',
            html: getBaseTemplate(content, 'Registro Pendiente'),
        });
        console.log(`✅ Pending notification sent to ${userEmail}`);
        return true;
    } catch (error) {
        console.error('❌ Error sending pending notification:', error);
        return false;
    }
}

/**
 * Send notification when a user is approved by admin
 */
export async function sendApprovalEmail(
    userEmail: string,
    userName: string
): Promise<boolean> {
    const loginUrl = ENV.BASE_URL ? `${ENV.BASE_URL}/login` : 'https://occultashield.com/login';

    const content = `
    <h1 style="margin: 0 0 16px; font-size: 28px; font-weight: 700; color: #f9fafb;">
      ¡Felicidades, ${userName}!
    </h1>
    <p style="margin: 0 0 24px; font-size: 16px; color: #d1d5db; line-height: 1.6;">
      Tu cuenta en OccultaShield ha sido aprobada.
    </p>
    
    <div style="background: rgba(34, 197, 94, 0.1); border: 1px solid rgba(34, 197, 94, 0.3); border-radius: 12px; padding: 20px; margin-bottom: 24px;">
      <div style="display: flex; align-items: center; gap: 12px;">
        <span style="font-size: 24px;">✅</span>
        <div>
          <p style="margin: 0; font-weight: 600; color: #22c55e; font-size: 16px;">
            Cuenta Activada
          </p>
          <p style="margin: 4px 0 0; color: #d1d5db; font-size: 14px;">
            Ya puedes acceder a todas las funcionalidades de la plataforma.
          </p>
        </div>
      </div>
    </div>
    
    <a href="${loginUrl}" style="display: inline-block; background: linear-gradient(135deg, #6366f1, #8b5cf6); color: white; text-decoration: none; padding: 14px 32px; border-radius: 8px; font-weight: 600; font-size: 16px;">
      Iniciar Sesión →
    </a>
    
    <p style="margin: 24px 0 0; font-size: 14px; color: #9ca3af; line-height: 1.6;">
      Gracias por unirte a la comunidad OccultaShield. Si tienes alguna pregunta, no dudes en contactarnos.
    </p>
  `;

    try {
        await getTransporter().sendMail({
            from: FROM_ADDRESS,
            to: userEmail,
            subject: '✅ OccultaShield - ¡Tu cuenta ha sido aprobada!',
            html: getBaseTemplate(content, 'Cuenta Aprobada'),
        });
        console.log(`✅ Approval email sent to ${userEmail}`);
        return true;
    } catch (error) {
        console.error('❌ Error sending approval email:', error);
        return false;
    }
}

/**
 * Send notification when a user is rejected
 */
export async function sendRejectionEmail(
    userEmail: string,
    userName: string
): Promise<boolean> {
    const content = `
    <h1 style="margin: 0 0 16px; font-size: 28px; font-weight: 700; color: #f9fafb;">
      Hola, ${userName}
    </h1>
    <p style="margin: 0 0 24px; font-size: 16px; color: #d1d5db; line-height: 1.6;">
      Lamentamos informarte que tu solicitud de acceso a OccultaShield no ha sido aprobada en esta ocasión.
    </p>
    
    <div style="background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 12px; padding: 20px; margin-bottom: 24px;">
      <div style="display: flex; align-items: center; gap: 12px;">
        <span style="font-size: 24px;">❌</span>
        <div>
          <p style="margin: 0; font-weight: 600; color: #ef4444; font-size: 16px;">
            Acceso Denegado
          </p>
          <p style="margin: 4px 0 0; color: #d1d5db; font-size: 14px;">
            Tu cuenta ha sido eliminada del sistema.
          </p>
        </div>
      </div>
    </div>
    
    <p style="margin: 0; font-size: 14px; color: #9ca3af; line-height: 1.6;">
      Si crees que esto es un error, puedes contactar con el administrador para más información.
    </p>
  `;

    try {
        await getTransporter().sendMail({
            from: FROM_ADDRESS,
            to: userEmail,
            subject: 'OccultaShield - Solicitud de acceso',
            html: getBaseTemplate(content, 'Acceso Denegado'),
        });
        console.log(`✅ Rejection email sent to ${userEmail}`);
        return true;
    } catch (error) {
        console.error('❌ Error sending rejection email:', error);
        return false;
    }
}
