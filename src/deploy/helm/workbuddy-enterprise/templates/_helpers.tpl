{{/* Common helpers for the workbuddy-enterprise chart */}}

{{- define "wb.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "wb.labels" -}}
helm.sh/chart: {{ include "wb.chart" . }}
app.kubernetes.io/name: workbuddy-enterprise
app.kubernetes.io/part-of: workbuddy-enterprise
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "wb.selectorLabels" -}}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{/*
Full image reference for a given service value map.
Usage: (must pass dict with "image" and root context)
*/}}
{{- define "wb.image" -}}
{{- $root := index . "root" -}}
{{- $svc := index . "svc" -}}
{{- $reg := $root.Values.global.imageRegistry -}}
{{- $repo := $svc.image.repository -}}
{{- $tag := $svc.image.tag | default $root.Values.image.tag -}}
{{- if $reg -}}
{{- printf "%s/%s:%s" $reg $repo $tag -}}
{{- else -}}
{{- printf "%s:%s" $repo $tag -}}
{{- end -}}
{{- end -}}

{{/*
Compute the PostgreSQL host: in-cluster service when enabled, else external host.
*/}}
{{- define "wb.pgHost" -}}
{{- if .Values.postgresql.enabled -}}
{{- printf "%s-postgresql" .Release.Name -}}
{{- else -}}
{{- .Values.postgresql.host -}}
{{- end -}}
{{- end -}}

{{/*
Compute the Redis host.
*/}}
{{- define "wb.redisHost" -}}
{{- if .Values.redis.enabled -}}
{{- printf "%s-redis" .Release.Name -}}
{{- else -}}
{{- .Values.redis.host -}}
{{- end -}}
{{- end -}}

{{/*
Compute the Qdrant host.
*/}}
{{- define "wb.qdrantHost" -}}
{{- if .Values.qdrant.enabled -}}
{{- printf "%s-qdrant" .Release.Name -}}
{{- else -}}
{{- .Values.qdrant.host -}}
{{- end -}}
{{- end -}}
