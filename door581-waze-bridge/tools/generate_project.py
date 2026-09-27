#!/usr/bin/env python3
from pathlib import Path
import hashlib, json

ROOT = Path(__file__).resolve().parents[1]
def ident(name): return hashlib.sha1(name.encode()).hexdigest()[:24].upper()
def q(v): return json.dumps(str(v))
objects=[]
def add(name,body):
    key=ident(name); objects.append(f"\t\t{key} = {{ {body} }};"); return key

swift=sorted((ROOT/"WazeBridge").glob("*.swift"))
source_refs=[]; source_builds=[]
for p in swift:
    ref=add("ref/"+p.name, f'isa = PBXFileReference; lastKnownFileType = sourcecode.swift; path = {q(p.name)}; sourceTree = "<group>";')
    source_refs.append(ref)
    source_builds.append(add("build/"+p.name, f"isa = PBXBuildFile; fileRef = {ref};"))
plistref=add("ref/plist",'isa = PBXFileReference; lastKnownFileType = text.plist.xml; path = Info.plist; sourceTree = "<group>";')
appref=add("ref/app",'isa = PBXFileReference; explicitFileType = wrapper.application; includeInIndex = 0; path = Door581WazeBridge.app; sourceTree = BUILT_PRODUCTS_DIR;')
group=add("sources",f'isa = PBXGroup; path = WazeBridge; sourceTree = "<group>"; children = ({",".join(source_refs+[plistref])},);')
products=add("products",f'isa = PBXGroup; name = Products; sourceTree = "<group>"; children = ({appref},);')
main=add("main",f'isa = PBXGroup; sourceTree = "<group>"; children = ({group},{products},);')
sources=add("phase/src",f'isa = PBXSourcesBuildPhase; buildActionMask = 2147483647; files = ({",".join(source_builds)},); runOnlyForDeploymentPostprocessing = 0;')
resources=add("phase/res",'isa = PBXResourcesBuildPhase; buildActionMask = 2147483647; files = (); runOnlyForDeploymentPostprocessing = 0;')
frameworks=add("phase/frameworks",'isa = PBXFrameworksBuildPhase; buildActionMask = 2147483647; files = (); runOnlyForDeploymentPostprocessing = 0;')

def config_list(prefix,target=False):
    refs=[]
    for mode in ["Debug","Release"]:
        settings={
          "CLANG_ENABLE_MODULES":"YES","CLANG_ENABLE_OBJC_ARC":"YES","SDKROOT":"iphoneos",
          "IPHONEOS_DEPLOYMENT_TARGET":"17.0","SWIFT_VERSION":"5.0",
          "SWIFT_OPTIMIZATION_LEVEL":"-Onone" if mode=="Debug" else "-O",
          "ENABLE_STRICT_OBJC_MSGSEND":"YES","GCC_C_LANGUAGE_STANDARD":"gnu17"
        }
        if target:
            settings.update({
              "PRODUCT_NAME":"Door581WazeBridge",
              "PRODUCT_BUNDLE_IDENTIFIER":"com.door581.wazebridge",
              "INFOPLIST_FILE":"WazeBridge/Info.plist","GENERATE_INFOPLIST_FILE":"NO",
              "TARGETED_DEVICE_FAMILY":"1","CODE_SIGN_STYLE":"Manual","CODE_SIGNING_ALLOWED":"NO",
              "CURRENT_PROJECT_VERSION":"1","MARKETING_VERSION":"0.1.0","ENABLE_BITCODE":"NO",
              "LD_RUNPATH_SEARCH_PATHS":"$(inherited) @executable_path/Frameworks"
            })
        body=" ".join(f"{k} = {q(v)};" for k,v in settings.items())
        refs.append(add(prefix+"/"+mode,f"isa = XCBuildConfiguration; name = {mode}; buildSettings = {{ {body} }};"))
    return add(prefix+"/list",f'isa = XCConfigurationList; buildConfigurations = ({",".join(refs)},); defaultConfigurationIsVisible = 0; defaultConfigurationName = Release;')

projectcfg=config_list("projectcfg"); targetcfg=config_list("targetcfg",True)
target=add("target",f'isa = PBXNativeTarget; name = Door581WazeBridge; productName = Door581WazeBridge; productReference = {appref}; productType = "com.apple.product-type.application"; buildConfigurationList = {targetcfg}; buildPhases = ({sources},{frameworks},{resources},); buildRules = (); dependencies = ();')
project=add("project",f'isa = PBXProject; attributes = {{ LastUpgradeCheck = 1600; }}; buildConfigurationList = {projectcfg}; compatibilityVersion = "Xcode 14.0"; developmentRegion = en; hasScannedForEncodings = 0; knownRegions = (en,Base,); mainGroup = {main}; productRefGroup = {products}; projectDirPath = ""; projectRoot = ""; targets = ({target},);')
projectdir=ROOT/"Door581WazeBridge.xcodeproj"; projectdir.mkdir(exist_ok=True)
(projectdir/"project.pbxproj").write_text('// !$*UTF8*$!\n{\n\tarchiveVersion = 1;\n\tclasses = {};\n\tobjectVersion = 56;\n\tobjects = {\n'+"\n".join(objects)+'\n\t};\n\trootObject = '+project+';\n}\n')
schemedir=projectdir/"xcshareddata/xcschemes"; schemedir.mkdir(parents=True,exist_ok=True)
scheme=f'''<?xml version="1.0" encoding="UTF-8"?>
<Scheme LastUpgradeVersion="1600" version="1.3">
 <BuildAction parallelizeBuildables="YES" buildImplicitDependencies="YES"><BuildActionEntries><BuildActionEntry buildForTesting="YES" buildForRunning="YES" buildForProfiling="YES" buildForArchiving="YES" buildForAnalyzing="YES"><BuildableReference BuildableIdentifier="primary" BlueprintIdentifier="{target}" BuildableName="Door581WazeBridge.app" BlueprintName="Door581WazeBridge" ReferencedContainer="container:Door581WazeBridge.xcodeproj"/></BuildActionEntry></BuildActionEntries></BuildAction>
 <LaunchAction buildConfiguration="Debug" launchStyle="0" useCustomWorkingDirectory="NO"><BuildableProductRunnable runnableDebuggingMode="0"><BuildableReference BuildableIdentifier="primary" BlueprintIdentifier="{target}" BuildableName="Door581WazeBridge.app" BlueprintName="Door581WazeBridge" ReferencedContainer="container:Door581WazeBridge.xcodeproj"/></BuildableProductRunnable></LaunchAction>
 <ProfileAction buildConfiguration="Release"/>
 <AnalyzeAction buildConfiguration="Debug"/>
 <ArchiveAction buildConfiguration="Release"/>
</Scheme>'''
(schemedir/"Door581WazeBridge.xcscheme").write_text(scheme)
print("Generated Door581WazeBridge.xcodeproj")
