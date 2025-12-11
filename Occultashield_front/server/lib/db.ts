/**
 * SurrealDB Connection Configuration
 * Establece y exporta la conexión a SurrealDB usando el driver oficial
 * Compatible con surreal-better-auth adapter
 */
import Surreal, { RecordId, StringRecordId } from 'surrealdb';
import { ENV } from './env';
console.log('Contenido completo de ENV:', JSON.stringify(ENV, null, 2));



// Instancia singleton de SurrealDB
let db: Surreal | null = null;
let connectionPromise: Promise<Surreal> | null = null;

/**
 * Mapeo de campos que son foreign keys (record links)
 * campo -> tabla referenciada
 * Usado para tablas personalizadas como processing_log
 */
const RECORD_LINK_FIELDS: Record<string, string> = {
  userId: 'user',
};

/**
 * Inicializa y retorna la conexión a SurrealDB
 * Usa patrón singleton para reutilizar la conexión
 */
export async function getDb(): Promise<Surreal> {
  // Si ya hay una conexión activa, retornarla
  if (db) return db;

  // Si ya hay una conexión en progreso, esperar a que termine
  if (connectionPromise) return connectionPromise;

  // Crear nueva conexión
  connectionPromise = (async () => {
    const instance = new Surreal();

    try {
      await instance.connect(ENV.SURREAL_URL);

      await instance.signin({
        username: ENV.SURREAL_USER,
        password: ENV.SURREAL_PASS,
      });

      await instance.use({
        namespace: ENV.SURREAL_NAMESPACE,
        database: ENV.SURREAL_DB,
      });

      console.log(`✅ Connected to SurrealDB at ${ENV.SURREAL_URL}`);
      console.log(`   Namespace: ${ENV.SURREAL_NAMESPACE}, Database: ${ENV.SURREAL_DB}`);

      db = instance;
      return instance;
    } catch (error) {
      console.error('❌ Failed to connect to SurrealDB:', error);
      connectionPromise = null;
      throw error;
    }
  })();

  return connectionPromise;
}

/**
 * Cierra la conexión a SurrealDB
 */
export async function closeDb(): Promise<void> {
  if (db) {
    await db.close();
    db = null;
    connectionPromise = null;
    console.log('🔌 SurrealDB connection closed');
  }
}

/**
 * Helper para parsear IDs de SurrealDB (RecordId | StringRecordId | string -> id simple)
 * SurrealDB v2 usa objetos RecordId
 */
export function parseRecordId(recordId: unknown): string {
  // Si es null o undefined
  if (recordId == null) return '';

  // Si es un objeto RecordId de SurrealDB v2
  if (recordId instanceof RecordId) {
    return String(recordId.id);
  }

  // Si es un StringRecordId
  if (recordId instanceof StringRecordId) {
    const str = recordId.toString();
    const colonIndex = str.indexOf(':');
    return colonIndex > -1 ? str.slice(colonIndex + 1) : str;
  }

  // Si es un string con formato "table:id"
  if (typeof recordId === 'string') {
    const colonIndex = recordId.indexOf(':');
    return colonIndex > -1 ? recordId.slice(colonIndex + 1) : recordId;
  }

  // Si es un objeto con propiedad id
  if (typeof recordId === 'object' && 'id' in recordId) {
    return parseRecordId((recordId as { id: unknown }).id);
  }

  // Si es un objeto con propiedad tb (tabla) y id
  if (typeof recordId === 'object' && 'tb' in recordId && 'id' in recordId) {
    return String((recordId as { tb: string; id: unknown }).id);
  }

  return String(recordId);
}

/**
 * Helper para crear un RecordId de SurrealDB (id -> table:id)
 * Compatible con SurrealDB v2
 */
export function createRecordId(table: string, id: string): StringRecordId {
  // Si ya tiene el prefijo de tabla, usar tal cual
  if (id.includes(':')) {
    return new StringRecordId(id);
  }
  return new StringRecordId(`${table}:${id}`);
}

/**
 * Convierte un valor a formato compatible con SurrealDB
 * Maneja fechas, RecordIds para foreign keys, etc.
 * Usado para tablas personalizadas (processing_log)
 *
 * @param value - Valor a convertir
 * @param fieldName - Nombre del campo (para detectar foreign keys)
 */
export function toSurrealValue(value: unknown, fieldName?: string): unknown {
  if (value === null || value === undefined) {
    return value;
  }

  // Si el campo es un foreign key conocido, convertir a record link
  if (fieldName && fieldName in RECORD_LINK_FIELDS && typeof value === 'string') {
    const table = RECORD_LINK_FIELDS[fieldName];
    // Si ya tiene el prefijo de tabla, usarlo tal cual
    if (value.includes(':')) {
      return new StringRecordId(value);
    }
    return new StringRecordId(`${table}:${value}`);
  }

  // Convertir Date a ISO string (SurrealDB acepta esto para campos datetime)
  if (value instanceof Date) {
    return value.toISOString();
  }

  // Si es un string, dejarlo como está
  if (typeof value === 'string') {
    return value;
  }

  // Arrays
  if (Array.isArray(value)) {
    return value.map((v) => toSurrealValue(v));
  }

  // Objetos (excepto tipos especiales)
  if (typeof value === 'object') {
    const result: Record<string, unknown> = {};
    for (const [key, val] of Object.entries(value)) {
      result[key] = toSurrealValue(val, key);
    }
    return result;
  }

  return value;
}

/**
 * Convierte un registro de SurrealDB a formato JavaScript normal
 * Maneja RecordIds, fechas, etc.
 * Convierte record links de vuelta a strings simples para Better-Auth
 */
export function fromSurrealRecord(record: unknown): Record<string, unknown> | null {
  if (!record || typeof record !== 'object') {
    return null;
  }

  const result: Record<string, unknown> = {};

  for (const [key, value] of Object.entries(record as Record<string, unknown>)) {
    // Convertir RecordId a string simple (extrae solo el ID sin la tabla)
    if (value instanceof RecordId || value instanceof StringRecordId) {
      result[key] = parseRecordId(value);
    }
    // Manejar objetos que parecen RecordId ({tb: 'table', id: 'xyz'})
    else if (value && typeof value === 'object' && 'tb' in value && 'id' in value) {
      result[key] = parseRecordId(value);
    }
    // Manejar campos que terminan en 'Id' y contienen ':' (formato string "table:id")
    else if (key.endsWith('Id') && typeof value === 'string' && value.includes(':')) {
      result[key] = parseRecordId(value);
    }
    // Convertir objetos Date de SurrealDB
    else if (value instanceof Date) {
      result[key] = value.toISOString();
    }
    // Todo lo demás, copiar directamente
    else {
      result[key] = value;
    }
  }

  return result;
}

/**
 * Prepara datos para insertar/actualizar en SurrealDB
 * Convierte campos foreign key a record links
 */
export function prepareDataForSurreal(data: Record<string, unknown>): Record<string, unknown> {
  const result: Record<string, unknown> = {};

  for (const [key, value] of Object.entries(data)) {
    result[key] = toSurrealValue(value, key);
  }

  return result;
}
