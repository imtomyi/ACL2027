<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:output method="text" encoding="UTF-8"/>
  <xsl:strip-space elements="*"/>

  <xsl:template match="text()"/>

  <xsl:template match="article-title|contrib-group|abstract|title|p|list-item|caption|table-wrap-foot|ack|fn|ref">
    <xsl:value-of select="normalize-space(.)"/>
    <xsl:text>&#10;</xsl:text>
  </xsl:template>

  <xsl:template match="article">
    <xsl:apply-templates select="front/article-meta/title-group/article-title"/>
    <xsl:apply-templates select="front/article-meta/contrib-group"/>
    <xsl:apply-templates select="front/article-meta/abstract"/>
    <xsl:apply-templates select="body|back"/>
  </xsl:template>

  <xsl:template match="body|back|sec|list|table-wrap|fig|ref-list">
    <xsl:apply-templates/>
  </xsl:template>
</xsl:stylesheet>
