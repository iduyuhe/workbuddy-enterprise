{{/*
Common container env for a WorkBuddy service.
Expects a dict: { "root": <root ctx>, "svc": <svc values>, "name": <svc key>, "secretName": <secret name> }
NOTE: service keys contain dashes (auth-service, model-gateway ...) so they MUST be
accessed via index, not dot notation: index $.Values.services "auth-service" "port"
*/}}
{{- define "wb.serviceEnv" -}}
{{- $root := .root -}}
{{- $svc := .svc -}}
{{- $name := .name -}}
{{- $secretName := .secretName -}}
{{- $svcs := $root.Values.services -}}
- name: PORT
  value: {{ $svc.port | quote }}
- name: POSTGRES_PASSWORD
  valueFrom:
    secretKeyRef:
      name: {{ $secretName }}
      key: postgres-password
- name: DATABASE_URL
  value: "postgresql+psycopg2://{{ $root.Values.postgresql.user }}:$(POSTGRES_PASSWORD)@{{ include "wb.pgHost" $root }}:{{ $root.Values.postgresql.port }}/{{ $root.Values.postgresql.database }}"
{{- if $root.Values.secrets.redisPassword }}
- name: REDIS_PASSWORD
  valueFrom:
    secretKeyRef:
      name: {{ $secretName }}
      key: redis-password
- name: REDIS_URL
  value: "redis://:$(REDIS_PASSWORD)@{{ include "wb.redisHost" $root }}:{{ $root.Values.redis.port }}/0"
{{- else }}
- name: REDIS_URL
  value: "redis://{{ include "wb.redisHost" $root }}:{{ $root.Values.redis.port }}/0"
{{- end }}
{{- if $root.Values.qdrant.enabled }}
- name: QDRANT_URL
  value: "http://{{ $root.Release.Name }}-qdrant:6333"
{{- else }}
- name: QDRANT_URL
  value: {{ $root.Values.qdrant.url | quote }}
{{- end }}
- name: JWT_SECRET
  valueFrom:
    secretKeyRef:
      name: {{ $secretName }}
      key: jwt-secret
{{- if $root.Values.secrets.oidcClientSecret }}
- name: OIDC_CLIENT_SECRET
  valueFrom:
    secretKeyRef:
      name: {{ $secretName }}
      key: oidc-client-secret
{{- end }}
{{- if $root.Values.secrets.llmApiKey }}
- name: LLM_API_KEY
  valueFrom:
    secretKeyRef:
      name: {{ $secretName }}
      key: llm-api-key
{{- end }}
- name: AUTH_SERVICE_URL
  value: "http://{{ $root.Release.Name }}-auth-service:{{ index $svcs "auth-service" "port" }}"
- name: MODEL_GATEWAY_URL
  value: "http://{{ $root.Release.Name }}-model-gateway:{{ index $svcs "model-gateway" "port" }}"
- name: SKILLS_SERVICE_URL
  value: "http://{{ $root.Release.Name }}-skills-registry:{{ index $svcs "skills-registry" "port" }}"
- name: MCP_SERVICE_URL
  value: "http://{{ $root.Release.Name }}-mcp-connector:{{ index $svcs "mcp-connector" "port" }}"
- name: KB_SERVICE_URL
  value: "http://{{ $root.Release.Name }}-knowledge-service:{{ index $svcs "knowledge-service" "port" }}"
- name: AUDIT_SERVICE_URL
  value: "http://{{ $root.Release.Name }}-audit-service:{{ index $svcs "audit-service" "port" }}"
- name: AGENT_SERVICE_URL
  value: "http://{{ $root.Release.Name }}-agent-service:{{ index $svcs "agent-service" "port" }}"
{{- with $svc.env }}
{{- toYaml . | nindent 0 }}
{{- end }}
{{- end -}}
