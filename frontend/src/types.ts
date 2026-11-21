// Espejo de src/tiendas3b/models/schemas.py. Solo Aaron cambia ese contrato.
export type Severity = "info" | "warning" | "critical";
export type Verdict = "Cumple" | "Requiere revisión" | "No cumple";
export type DocType =
  | "escrituras"
  | "predial"
  | "alineamiento_y_numero_oficial"
  | "uso_de_suelo"
  | "desconocido";

export interface Evidence {
  document_name: string;
  page: number | null;
  snippet: string;
}

export interface ExtractedField {
  name: string;
  value: string | null;
  evidence: Evidence | null;
  confidence: number;
  method: string;
}

export interface RuleEvaluation {
  rule_id: string;
  description: string;
  passed: boolean;
  details: string;
  evidence: Evidence[];
  severity: Severity;
}

export interface DocumentAnalysis {
  document_name: string;
  document_type: DocType;
  extracted_fields: ExtractedField[];
  rule_evaluations: RuleEvaluation[];
  missing_fields: string[];
  classification_confidence: number;
  classification_method: string;
}

export interface CrossIssue {
  field_name: string;
  description: string;
  severity: Severity;
  documents_involved: string[];
  values_found: Record<string, string>;
  evidence: Evidence[];
}

export interface AgentStep {
  agent: string;
  ms: number;
  detail: string;
}

export interface Report {
  expediente_id: string;
  documents_received: string[];
  missing_document_types: DocType[];
  document_analyses: DocumentAnalysis[];
  cross_validation_issues: CrossIssue[];
  confidence: number;
  recommendation: Verdict;
  explanation: string;
  reasons: string[];
  trace: AgentStep[];
  processing_ms: number;
  llm_mode: string;
}

export interface ApiStatus {
  api: string;
  version: string;
  llm_mode: string;
  llm_reachable: boolean;
  cartuchos: string[];
  reglas_activas: number;
}

export interface DemoCase {
  caso: string;
  expediente_id: string;
  descripcion: string;
  esperado: Verdict;
  documentos: string[];
}

/** Un expediente en la bandeja. Solo se guardan ids y resultados, nunca documentos. */
export interface Entry {
  id: string;
  createdAt: number;
  status: "procesando" | "listo" | "error";
  report?: Report;
  error?: string;
}
