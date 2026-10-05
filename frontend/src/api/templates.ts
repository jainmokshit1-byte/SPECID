// PRD API-15 (FR-401): the rulebook, read-only.

import { apiGet } from "./client";

export interface TemplateSummary {
  id: string;
  category: string;
  version: number;
  status: string;
  critical_default: boolean;
  core: string[];
  extended: string[];
  rules: number;
}

export interface TemplateDetail extends Omit<TemplateSummary, "rules"> {
  tolerant: string[];
  make: string[];
  value_domains: Record<string, (string | number)[]>;
  aliases: Record<string, Record<string, string>>;
  rule_text: Record<string, string>;
  rules: string[];
  implied: Record<string, unknown>[];
  class_path: string[] | null;
  unspsc: string | null;
}

export const listTemplates = () => apiGet<TemplateSummary[]>("/templates");
export const getTemplate = (id: string) => apiGet<TemplateDetail>(`/templates/${id}`);
