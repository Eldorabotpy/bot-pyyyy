[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

Add-Type -AssemblyName System.Drawing

$projectRoot = Split-Path -Parent $PSScriptRoot
$sourceMapPath = Join-Path $projectRoot 'static\regions\capital_eldora.tmj'
$sourceImagePath = Join-Path $projectRoot 'static\images\regions\capital_eldora\tilesets\capital eldora.png'
$runtimeMapDirectory = Join-Path $projectRoot 'static\regions\generated'
$runtimeImageDirectory = Join-Path $projectRoot 'static\images\regions\capital_eldora\tilesets\generated'
$runtimeMapPath = Join-Path $runtimeMapDirectory 'capital_eldora.runtime.tmj'
$runtimeImagePath = Join-Path $runtimeImageDirectory 'capital_eldora_compact.png'

if (-not (Test-Path -LiteralPath $sourceMapPath -PathType Leaf)) {
    throw "Mapa fonte do Tiled não encontrado: $sourceMapPath"
}
if (-not (Test-Path -LiteralPath $sourceImagePath -PathType Leaf)) {
    throw "Atlas fonte do Tiled não encontrado: $sourceImagePath"
}

$map = Get-Content -LiteralPath $sourceMapPath -Raw -Encoding UTF8 | ConvertFrom-Json -AsHashtable
$mainTileset = @($map.tilesets | Where-Object { $_.name -eq 'capital eldora' })
if ($mainTileset.Count -ne 1) {
    throw "Esperava exatamente um tileset 'capital eldora'; encontrados: $($mainTileset.Count)."
}
$tileset = $mainTileset[0]

$tileWidth = [int]$tileset.tilewidth
$tileHeight = [int]$tileset.tileheight
$sourceColumns = [int]$tileset.columns
$oldTileCount = [int]$tileset.tilecount
$firstGid = [int]$tileset.firstgid
$oldLastGid = $firstGid + $oldTileCount - 1
$gidMask = [uint64]268435455
$transformMask = [uint64]4026531840
$usedTileIds = [System.Collections.Generic.HashSet[int]]::new()

function Get-LocalTileId([object]$rawGid) {
    if ($null -eq $rawGid) { return -1 }
    if ($rawGid -isnot [ValueType]) {
        throw "GID de mapa com tipo inesperado: $($rawGid.GetType().FullName)"
    }

    $gidValue = [uint64]$rawGid
    $plainGid = [int]($gidValue -band $gidMask)
    if ($plainGid -ge $firstGid -and $plainGid -le $oldLastGid) {
        return $plainGid - $firstGid
    }
    return -1
}

function Add-ReferencedGid([object]$rawGid) {
    $localId = Get-LocalTileId $rawGid
    if ($localId -ge 0) { [void]$usedTileIds.Add($localId) }
}

function Collect-LayerGids([object[]]$layers) {
    foreach ($layer in $layers) {
        if ($layer.type -eq 'tilelayer') {
            if ($layer.Contains('data')) {
                if ($layer.data -isnot [array]) {
                    throw "Camada '$($layer.name)' usa dados que não são uma lista de GIDs; geração interrompida sem alterar o mapa fonte."
                }
                foreach ($gid in $layer.data) { Add-ReferencedGid $gid }
            }
            if ($layer.Contains('chunks')) {
                foreach ($chunk in $layer.chunks) {
                    if ($chunk.data -isnot [array]) {
                        throw "Chunk da camada '$($layer.name)' não contém uma lista de GIDs."
                    }
                    foreach ($gid in $chunk.data) { Add-ReferencedGid $gid }
                }
            }
        }
        elseif ($layer.type -eq 'objectgroup') {
            foreach ($object in $layer.objects) {
                if ($object.Contains('gid')) { Add-ReferencedGid $object.gid }
            }
        }
        elseif ($layer.type -eq 'group') {
            Collect-LayerGids @($layer.layers)
        }
    }
}

Collect-LayerGids @($map.layers)

$tileDefinitions = @($tileset.tiles)
$tileDefinitionsById = @{}
foreach ($tileDefinition in $tileDefinitions) {
    $tileId = [int]$tileDefinition.id
    $tileDefinitionsById[$tileId] = $tileDefinition
    if ($tileDefinition.Contains('image')) {
        throw "O tileset contém imagens individuais por tile; este compactador espera uma imagem atlas única."
    }
}

# Inclui os quadros referenciados por tiles animados antes de criar o atlas.
$pendingTileIds = [System.Collections.Generic.Queue[int]]::new()
foreach ($tileId in $usedTileIds) { $pendingTileIds.Enqueue($tileId) }
while ($pendingTileIds.Count -gt 0) {
    $tileId = $pendingTileIds.Dequeue()
    $tileDefinition = $tileDefinitionsById[$tileId]
    if ($null -eq $tileDefinition -or -not $tileDefinition.Contains('animation')) { continue }

    foreach ($frame in $tileDefinition.animation) {
        $frameId = [int]$frame.tileid
        if ($frameId -lt 0 -or $frameId -ge $oldTileCount) {
            throw "Animação do tile $tileId aponta para um ID fora do tileset: $frameId."
        }
        if ($usedTileIds.Add($frameId)) { $pendingTileIds.Enqueue($frameId) }
    }
}

if ($tileset.Contains('wangsets') -and @($tileset.wangsets).Count -gt 0) {
    throw 'O tileset possui Wang Sets. Atualize o compactador para remapear esses IDs antes de gerar o mapa.'
}

$bitmap = [System.Drawing.Bitmap]::new($sourceImagePath)
try {
    if ($sourceColumns -le 0 -or $tileWidth -le 0 -or $tileHeight -le 0 -or $oldTileCount -le 0) {
        throw 'Metadados inválidos de grade no tileset fonte.'
    }
    if ($bitmap.Width -ne [int]$tileset.imagewidth -or $bitmap.Height -ne [int]$tileset.imageheight) {
        throw "Dimensões do PNG ($($bitmap.Width)x$($bitmap.Height)) não correspondem ao TMJ ($($tileset.imagewidth)x$($tileset.imageheight))."
    }
    if ($bitmap.Width -lt ($sourceColumns * $tileWidth) -or $bitmap.Height -lt ([math]::Ceiling($oldTileCount / $sourceColumns) * $tileHeight)) {
        throw 'As dimensões do atlas não cobrem todos os tiles definidos no Tiled.'
    }

    $sortedTileIds = @($usedTileIds | Sort-Object)
    if ($sortedTileIds.Count -eq 0) { throw 'Nenhum tile do atlas principal foi encontrado no mapa.' }

    # Mantém as dimensões próximas de um quadrado para reduzir pixels vazios.
    $packedColumns = [int][math]::Ceiling([math]::Sqrt($sortedTileIds.Count))
    $packedRows = [int][math]::Ceiling($sortedTileIds.Count / $packedColumns)
    # Uma borda de 1 px, com 2 px de espaçamento, evita que o filtro linear
    # do WebGL misture pixels do tile vizinho quando a câmera usa escala fracionada.
    $atlasMargin = 1
    $atlasSpacing = 2
    $packedWidth = (2 * $atlasMargin) + ($packedColumns * $tileWidth) + (($packedColumns - 1) * $atlasSpacing)
    $packedHeight = (2 * $atlasMargin) + ($packedRows * $tileHeight) + (($packedRows - 1) * $atlasSpacing)
    $newIdByOldId = @{}
    for ($index = 0; $index -lt $sortedTileIds.Count; $index++) {
        $newIdByOldId[[int]$sortedTileIds[$index]] = $index
    }
    $packedLastGid = $firstGid + $sortedTileIds.Count - 1
    foreach ($otherTileset in $map.tilesets) {
        if ($otherTileset.name -eq $tileset.name) { continue }
        $otherFirstGid = [int]$otherTileset.firstgid
        $otherLastGid = $otherFirstGid + [int]$otherTileset.tilecount - 1
        if ($otherFirstGid -le $packedLastGid -and $otherLastGid -ge $firstGid) {
            throw "O GID compacto pisaria no tileset '$($otherTileset.name)'; nenhuma saída foi publicada."
        }
    }

    $atlas = [System.Drawing.Bitmap]::new(
        $packedWidth,
        $packedHeight,
        [System.Drawing.Imaging.PixelFormat]::Format32bppArgb
    )
    $sourceData = $null
    $targetData = $null
    $temporaryImagePath = Join-Path $runtimeImageDirectory ('.capital_eldora_compact.' + [guid]::NewGuid().ToString('N') + '.tmp.png')
    $temporaryMapPath = Join-Path $runtimeMapDirectory ('.capital_eldora.runtime.' + [guid]::NewGuid().ToString('N') + '.tmp')

    try {
        [void](New-Item -ItemType Directory -Path $runtimeMapDirectory -Force)
        [void](New-Item -ItemType Directory -Path $runtimeImageDirectory -Force)

        $fullSourceRect = [System.Drawing.Rectangle]::new(0, 0, $bitmap.Width, $bitmap.Height)
        $sourceData = $bitmap.LockBits(
            $fullSourceRect,
            [System.Drawing.Imaging.ImageLockMode]::ReadOnly,
            [System.Drawing.Imaging.PixelFormat]::Format32bppArgb
        )
        $fullTargetRect = [System.Drawing.Rectangle]::new(0, 0, $packedWidth, $packedHeight)
        $targetData = $atlas.LockBits(
            $fullTargetRect,
            [System.Drawing.Imaging.ImageLockMode]::WriteOnly,
            [System.Drawing.Imaging.PixelFormat]::Format32bppArgb
        )

        $tileRowBytes = $tileWidth * 4
        $pixelBytes = 4
        $rowBuffer = [byte[]]::new($tileRowBytes)
        $topRowBuffer = [byte[]]::new($tileRowBytes)
        $bottomRowBuffer = [byte[]]::new($tileRowBytes)
        $edgePixelBuffer = [byte[]]::new($pixelBytes)
        for ($index = 0; $index -lt $sortedTileIds.Count; $index++) {
            $oldId = [int]$sortedTileIds[$index]
            $sourceX = ($oldId % $sourceColumns) * $tileWidth
            $sourceY = [int][math]::Floor($oldId / $sourceColumns) * $tileHeight
            $targetX = $atlasMargin + (($index % $packedColumns) * ($tileWidth + $atlasSpacing))
            $targetY = $atlasMargin + ([int][math]::Floor($index / $packedColumns) * ($tileHeight + $atlasSpacing))

            for ($row = 0; $row -lt $tileHeight; $row++) {
                $sourceOffset = (($sourceY + $row) * $sourceData.Stride) + ($sourceX * 4)
                $targetOffset = (($targetY + $row) * $targetData.Stride) + ($targetX * 4)
                $sourcePointer = [System.IntPtr]::Add($sourceData.Scan0, $sourceOffset)
                $targetPointer = [System.IntPtr]::Add($targetData.Scan0, $targetOffset)
                [System.Runtime.InteropServices.Marshal]::Copy($sourcePointer, $rowBuffer, 0, $tileRowBytes)
                [System.Runtime.InteropServices.Marshal]::Copy($rowBuffer, 0, $targetPointer, $tileRowBytes)

                # Extruda as bordas nas áreas transparentes do gutter.
                [System.Array]::Copy($rowBuffer, 0, $edgePixelBuffer, 0, $pixelBytes)
                $leftPointer = [System.IntPtr]::Add($targetPointer, -$pixelBytes)
                [System.Runtime.InteropServices.Marshal]::Copy($edgePixelBuffer, 0, $leftPointer, $pixelBytes)
                [System.Array]::Copy($rowBuffer, $tileRowBytes - $pixelBytes, $edgePixelBuffer, 0, $pixelBytes)
                $rightPointer = [System.IntPtr]::Add($targetPointer, $tileRowBytes)
                [System.Runtime.InteropServices.Marshal]::Copy($edgePixelBuffer, 0, $rightPointer, $pixelBytes)

                if ($row -eq 0) {
                    [System.Array]::Copy($rowBuffer, $topRowBuffer, $tileRowBytes)
                }
                if ($row -eq ($tileHeight - 1)) {
                    [System.Array]::Copy($rowBuffer, $bottomRowBuffer, $tileRowBytes)
                }
            }

            $topPointer = [System.IntPtr]::Add($targetData.Scan0, (($targetY - 1) * $targetData.Stride) + ($targetX * 4))
            $bottomPointer = [System.IntPtr]::Add($targetData.Scan0, (($targetY + $tileHeight) * $targetData.Stride) + ($targetX * 4))
            [System.Runtime.InteropServices.Marshal]::Copy($topRowBuffer, 0, $topPointer, $tileRowBytes)
            [System.Runtime.InteropServices.Marshal]::Copy($bottomRowBuffer, 0, $bottomPointer, $tileRowBytes)

            [System.Array]::Copy($topRowBuffer, 0, $edgePixelBuffer, 0, $pixelBytes)
            $topLeftPointer = [System.IntPtr]::Add($topPointer, -$pixelBytes)
            [System.Runtime.InteropServices.Marshal]::Copy($edgePixelBuffer, 0, $topLeftPointer, $pixelBytes)
            $topRightPointer = [System.IntPtr]::Add($topPointer, $tileRowBytes)
            [System.Array]::Copy($topRowBuffer, $tileRowBytes - $pixelBytes, $edgePixelBuffer, 0, $pixelBytes)
            [System.Runtime.InteropServices.Marshal]::Copy($edgePixelBuffer, 0, $topRightPointer, $pixelBytes)

            [System.Array]::Copy($bottomRowBuffer, 0, $edgePixelBuffer, 0, $pixelBytes)
            $bottomLeftPointer = [System.IntPtr]::Add($bottomPointer, -$pixelBytes)
            [System.Runtime.InteropServices.Marshal]::Copy($edgePixelBuffer, 0, $bottomLeftPointer, $pixelBytes)
            $bottomRightPointer = [System.IntPtr]::Add($bottomPointer, $tileRowBytes)
            [System.Array]::Copy($bottomRowBuffer, $tileRowBytes - $pixelBytes, $edgePixelBuffer, 0, $pixelBytes)
            [System.Runtime.InteropServices.Marshal]::Copy($edgePixelBuffer, 0, $bottomRightPointer, $pixelBytes)
        }

        $atlas.UnlockBits($targetData)
        $targetData = $null
        $bitmap.UnlockBits($sourceData)
        $sourceData = $null
        $atlas.Save($temporaryImagePath, [System.Drawing.Imaging.ImageFormat]::Png)
    }
    finally {
        if ($null -ne $targetData) { $atlas.UnlockBits($targetData) }
        if ($null -ne $sourceData) { $bitmap.UnlockBits($sourceData) }
        $atlas.Dispose()
    }

    # Confere os pixels decodificados em todos os tiles usados antes de publicar
    # o atlas derivado. O arquivo fonte e o mapa fonte nunca são sobrescritos.
    $readPackedPixels = {
        param([string]$Path, [bool]$IsPacked)
        $readBitmap = [System.Drawing.Bitmap]::new($Path)
        $readData = $null
        try {
            $rect = [System.Drawing.Rectangle]::new(0, 0, $readBitmap.Width, $readBitmap.Height)
            $readData = $readBitmap.LockBits(
                $rect,
                [System.Drawing.Imaging.ImageLockMode]::ReadOnly,
                [System.Drawing.Imaging.PixelFormat]::Format32bppArgb
            )
            $pixels = [byte[]]::new($sortedTileIds.Count * $tileWidth * $tileHeight * 4)
            $offset = 0
            for ($index = 0; $index -lt $sortedTileIds.Count; $index++) {
                if ($IsPacked) {
                    $x = $atlasMargin + (($index % $packedColumns) * ($tileWidth + $atlasSpacing))
                    $y = $atlasMargin + ([int][math]::Floor($index / $packedColumns) * ($tileHeight + $atlasSpacing))
                }
                else {
                    $tileId = [int]$sortedTileIds[$index]
                    $x = ($tileId % $sourceColumns) * $tileWidth
                    $y = [int][math]::Floor($tileId / $sourceColumns) * $tileHeight
                }

                for ($row = 0; $row -lt $tileHeight; $row++) {
                    $pixelOffset = (($y + $row) * $readData.Stride) + ($x * 4)
                    $pointer = [System.IntPtr]::Add($readData.Scan0, $pixelOffset)
                    [System.Runtime.InteropServices.Marshal]::Copy($pointer, $pixels, $offset, $tileRowBytes)
                    $offset += $tileRowBytes
                }
            }
            return [Convert]::ToHexString([System.Security.Cryptography.SHA256]::HashData($pixels))
        }
        finally {
            if ($null -ne $readData) { $readBitmap.UnlockBits($readData) }
            $readBitmap.Dispose()
        }
    }

    $sourcePixelHash = & $readPackedPixels $sourceImagePath $false
    $packedPixelHash = & $readPackedPixels $temporaryImagePath $true
    if ($sourcePixelHash -ne $packedPixelHash) {
        throw 'A verificação de pixels falhou; o atlas compacto não será publicado.'
    }

    function Remap-Gid([object]$rawGid) {
        if ($null -eq $rawGid -or [uint64]$rawGid -eq 0) { return $rawGid }
        $gidValue = [uint64]$rawGid
        $plainGid = [int]($gidValue -band $gidMask)
        if ($plainGid -lt $firstGid -or $plainGid -gt $oldLastGid) { return $rawGid }

        $oldId = $plainGid - $firstGid
        if (-not $newIdByOldId.ContainsKey($oldId)) {
            throw "Mapa referencia tile não incluído no atlas compacto: $oldId."
        }
        $flags = $gidValue -band $transformMask
        $newGid = [uint64]($firstGid + [int]$newIdByOldId[$oldId])
        return [uint64]($flags -bor $newGid)
    }

    function Remap-LayerGids([object[]]$layers) {
        foreach ($layer in $layers) {
            if ($layer.type -eq 'tilelayer') {
                if ($layer.Contains('data')) {
                    for ($index = 0; $index -lt $layer.data.Count; $index++) {
                        $layer.data[$index] = Remap-Gid $layer.data[$index]
                    }
                }
                if ($layer.Contains('chunks')) {
                    foreach ($chunk in $layer.chunks) {
                        for ($index = 0; $index -lt $chunk.data.Count; $index++) {
                            $chunk.data[$index] = Remap-Gid $chunk.data[$index]
                        }
                    }
                }
            }
            elseif ($layer.type -eq 'objectgroup') {
                foreach ($object in $layer.objects) {
                    if ($object.Contains('gid')) { $object.gid = Remap-Gid $object.gid }
                }
            }
            elseif ($layer.type -eq 'group') {
                Remap-LayerGids @($layer.layers)
            }
        }
    }

    Remap-LayerGids @($map.layers)

    $packedDefinitions = [System.Collections.Generic.List[object]]::new()
    foreach ($tileDefinition in $tileDefinitions) {
        $oldId = [int]$tileDefinition.id
        if (-not $newIdByOldId.ContainsKey($oldId)) { continue }
        $tileDefinition.id = [int]$newIdByOldId[$oldId]
        if ($tileDefinition.Contains('animation')) {
            foreach ($frame in $tileDefinition.animation) {
                $frame.tileid = [int]$newIdByOldId[[int]$frame.tileid]
            }
        }
        $packedDefinitions.Add($tileDefinition)
    }

    $tileset.image = '../../images/regions/capital_eldora/tilesets/generated/capital_eldora_compact.png'
    $tileset.imagewidth = $packedWidth
    $tileset.imageheight = $packedHeight
    $tileset.columns = $packedColumns
    $tileset.margin = $atlasMargin
    $tileset.spacing = $atlasSpacing
    $tileset.tilecount = $sortedTileIds.Count
    $tileset.tiles = $packedDefinitions.ToArray()

    # O mapa de runtime fica em static/regions/generated, uma pasta abaixo da
    # fonte. Ajusta os outros tilesets embutidos para continuar apontando para
    # static/images após essa mudança de diretório.
    foreach ($runtimeTileset in $map.tilesets) {
        if (
            $runtimeTileset.name -ne $tileset.name -and
            -not [string]::IsNullOrWhiteSpace([string]$runtimeTileset.image) -and
            $runtimeTileset.image.StartsWith('../images/')
        ) {
            $runtimeTileset.image = "../$($runtimeTileset.image)"
        }
    }

    $runtimeJson = ConvertTo-Json -InputObject $map -Depth 100 -Compress
    [System.IO.File]::WriteAllText($temporaryMapPath, $runtimeJson, [System.Text.UTF8Encoding]::new($false))

    # Replace only known generated outputs, keeping the two source files intact.
    Move-Item -LiteralPath $temporaryImagePath -Destination $runtimeImagePath -Force
    Move-Item -LiteralPath $temporaryMapPath -Destination $runtimeMapPath -Force

    $sourceImageBytes = (Get-Item -LiteralPath $sourceImagePath).Length
    $runtimeImageBytes = (Get-Item -LiteralPath $runtimeImagePath).Length
    $sourcePixels = [long]$bitmap.Width * [long]$bitmap.Height
    $runtimePixels = [long]$packedWidth * [long]$packedHeight
    $pixelReduction = [math]::Round((1 - ($runtimePixels / $sourcePixels)) * 100, 1)
    $byteReduction = [math]::Round((1 - ($runtimeImageBytes / $sourceImageBytes)) * 100, 1)

    [pscustomobject]@{
        RuntimeMap = $runtimeMapPath
        RuntimeAtlas = $runtimeImagePath
        OriginalAtlas = '{0}x{1}, {2:N2} MiB' -f $bitmap.Width, $bitmap.Height, ($sourceImageBytes / 1MB)
        CompactAtlas = '{0}x{1}, {2:N2} MiB' -f $packedWidth, $packedHeight, ($runtimeImageBytes / 1MB)
        TilesKept = $sortedTileIds.Count
        TilesOriginal = $oldTileCount
        AtlasPixelReductionPercent = $pixelReduction
        AtlasFileSizeReductionPercent = $byteReduction
        SourcePixelHash = $sourcePixelHash
        CompactPixelHash = $packedPixelHash
    } | Format-List
}
finally {
    $bitmap.Dispose()
}
