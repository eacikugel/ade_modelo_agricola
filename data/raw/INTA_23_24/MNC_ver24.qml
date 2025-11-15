<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis version="3.22.14-Białowieża" styleCategories="AllStyleCategories" maxScale="0" hasScaleBasedVisibilityFlag="0" minScale="1e+08">
  <flags>
    <Identifiable>1</Identifiable>
    <Removable>1</Removable>
    <Searchable>1</Searchable>
    <Private>0</Private>
  </flags>
  <temporal enabled="0" mode="0" fetchMode="0">
    <fixedRange>
      <start></start>
      <end></end>
    </fixedRange>
  </temporal>
  <customproperties>
    <Option type="Map">
      <Option value="false" type="QString" name="WMSBackgroundLayer"/>
      <Option value="false" type="QString" name="WMSPublishDataSourceUrl"/>
      <Option value="0" type="QString" name="embeddedWidgets/count"/>
      <Option value="Value" type="QString" name="identify/format"/>
    </Option>
  </customproperties>
  <pipe-data-defined-properties>
    <Option type="Map">
      <Option value="" type="QString" name="name"/>
      <Option name="properties"/>
      <Option value="collection" type="QString" name="type"/>
    </Option>
  </pipe-data-defined-properties>
  <pipe>
    <provider>
      <resampling enabled="false" zoomedOutResamplingMethod="nearestNeighbour" zoomedInResamplingMethod="nearestNeighbour" maxOversampling="2"/>
    </provider>
    <rasterrenderer classificationMin="10" type="singlebandpseudocolor" classificationMax="255" opacity="1" alphaBand="-1" nodataColor="" band="1">
      <rasterTransparency/>
      <minMaxOrigin>
        <limits>None</limits>
        <extent>WholeRaster</extent>
        <statAccuracy>Estimated</statAccuracy>
        <cumulativeCutLower>0.02</cumulativeCutLower>
        <cumulativeCutUpper>0.98</cumulativeCutUpper>
        <stdDevFactor>2</stdDevFactor>
      </minMaxOrigin>
      <rastershader>
        <colorrampshader minimumValue="10" classificationMode="1" clip="0" maximumValue="255" labelPrecision="0" colorRampType="INTERPOLATED">
          <colorramp type="gradient" name="[source]">
            <Option type="Map">
              <Option value="0,66,255,255" type="QString" name="color1"/>
              <Option value="255,255,255,0" type="QString" name="color2"/>
              <Option value="0" type="QString" name="discrete"/>
              <Option value="gradient" type="QString" name="rampType"/>
              <Option value="0.00408163;51,152,32,255:0.00816327;164,29,226,255:0.0122449;240,34,219,255:0.0163265;252,193,179,255:0.0204082;183,185,189,255:0.0244898;251,255,5,255:0.0285714;29,30,51,255:0.0326531;30,15,107,255:0.0367347;163,33,2,255:0.044898;100,107,99,255:0.0489796;230,240,194,255:0.0653061;255,80,80,255:0.0734694;102,153,255,255:0.0816327;0,150,136,255:0.0857143;0,0,0,255" type="QString" name="stops"/>
            </Option>
            <prop k="color1" v="0,66,255,255"/>
            <prop k="color2" v="255,255,255,0"/>
            <prop k="discrete" v="0"/>
            <prop k="rampType" v="gradient"/>
            <prop k="stops" v="0.00408163;51,152,32,255:0.00816327;164,29,226,255:0.0122449;240,34,219,255:0.0163265;252,193,179,255:0.0204082;183,185,189,255:0.0244898;251,255,5,255:0.0285714;29,30,51,255:0.0326531;30,15,107,255:0.0367347;163,33,2,255:0.044898;100,107,99,255:0.0489796;230,240,194,255:0.0653061;255,80,80,255:0.0734694;102,153,255,255:0.0816327;0,150,136,255:0.0857143;0,0,0,255"/>
          </colorramp>
          <item value="10" alpha="255" color="#0042ff" label="Maíz"/>
          <item value="11" alpha="255" color="#339820" label="Soja"/>
          <item value="12" alpha="255" color="#a41de2" label="Girasol"/>
          <item value="13" alpha="255" color="#f022db" label="Poroto"/>
          <item value="14" alpha="255" color="#fcc1b3" label="Caña de azúcar"/>
          <item value="15" alpha="255" color="#b7b9bd" label="Algodón"/>
          <item value="16" alpha="255" color="#fbff05" label="Maní"/>
          <item value="17" alpha="255" color="#1d1e33" label="Arroz"/>
          <item value="18" alpha="255" color="#1e0f6b" label="Sorgo"/>
          <item value="19" alpha="255" color="#a32102" label="Girasol-CV"/>
          <item value="21" alpha="255" color="#646b63" label="Barbecho"/>
          <item value="22" alpha="255" color="#e6f0c2" label="No agrícola"/>
          <item value="26" alpha="255" color="#ff5050" label="Papa"/>
          <item value="28" alpha="255" color="#6699ff" label="Verdeo de Sorgo"/>
          <item value="30" alpha="255" color="#009688" label="Tabaco"/>
          <item value="31" alpha="255" color="#000000" label="Máscara"/>
          <item value="255" alpha="0" color="#ffffff" label="255"/>
          <rampLegendSettings minimumLabel="" useContinuousLegend="0" suffix="" direction="0" maximumLabel="" prefix="" orientation="2">
            <numericFormat id="basic">
              <Option type="Map">
                <Option value="" type="QChar" name="decimal_separator"/>
                <Option value="6" type="int" name="decimals"/>
                <Option value="0" type="int" name="rounding_type"/>
                <Option value="false" type="bool" name="show_plus"/>
                <Option value="true" type="bool" name="show_thousand_separator"/>
                <Option value="false" type="bool" name="show_trailing_zeros"/>
                <Option value="" type="QChar" name="thousand_separator"/>
              </Option>
            </numericFormat>
          </rampLegendSettings>
        </colorrampshader>
      </rastershader>
    </rasterrenderer>
    <brightnesscontrast contrast="0" gamma="1" brightness="0"/>
    <huesaturation saturation="0" grayscaleMode="0" colorizeGreen="128" invertColors="0" colorizeOn="0" colorizeBlue="128" colorizeStrength="100" colorizeRed="255"/>
    <rasterresampler maxOversampling="2"/>
    <resamplingStage>resamplingFilter</resamplingStage>
  </pipe>
  <blendMode>0</blendMode>
</qgis>
