from django.contrib import admin

from .models import CitationSource, Embedding, RetrievalLog, VectorChunk, VectorDocument

admin.site.register(VectorDocument)
admin.site.register(VectorChunk)
admin.site.register(Embedding)
admin.site.register(RetrievalLog)
admin.site.register(CitationSource)
