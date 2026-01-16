/**
 * Tutorial Content - Comprehensive guides for each workflow stage
 *
 * IMPORTANT: Keep this file updated when adding new features or UI changes!
 * See CLAUDE.md for maintenance instructions.
 */

export interface TermDefinition {
  term: string;
  definition: string;
  example?: string;
}

export interface TutorialStep {
  title: string;
  description: string;
  tip?: string;
}

export interface TutorialSection {
  title: string;
  content: string;
  steps?: TutorialStep[];
  terminology?: TermDefinition[];
  tips?: string[];
  warnings?: string[];
}

export interface StageTutorial {
  id: string;
  stageName: string;
  title: string;
  introduction: string;
  sections: TutorialSection[];
  quickStart: string[];
  commonIssues?: { problem: string; solution: string }[];
}

// ============================================================================
// UPLOAD STAGE TUTORIAL
// ============================================================================

export const uploadStageTutorial: StageTutorial = {
  id: 'upload',
  stageName: 'Upload',
  title: 'Source Image Creation',
  introduction:
    'This is the starting point for creating your 3D asset. You can either upload an existing image or generate one from a text description. The quality of your source image directly affects the final 3D model quality.',

  sections: [
    {
      title: 'Upload Image Tab',
      content:
        'Upload an existing image to convert into a 3D model. The AI works best with images that have a clear subject and simple background.',
      steps: [
        {
          title: 'Select an Image',
          description:
            'Drag and drop an image onto the upload area, or click to browse your files. Supported formats: PNG, JPG, WEBP (up to 10MB).',
          tip: 'For best results, use images with a single object centered in frame.',
        },
        {
          title: 'Review Preview',
          description:
            "Your image will appear in the preview area. Check that the subject is clear and well-lit. You can remove the image and try another if needed.",
        },
        {
          title: 'Name Your Asset',
          description:
            "Enter a descriptive name for your asset. This helps you find it later in your library. If left blank, the filename will be used.",
        },
        {
          title: 'Choose Quality Preset',
          description:
            'Select how detailed you want the 3D model. Higher quality takes longer but produces more detailed results.',
        },
      ],
      terminology: [
        {
          term: 'Source Image',
          definition:
            'The 2D picture that the AI analyzes to create a 3D model. Think of it as the "reference photo" for your 3D asset.',
          example: 'A photo of a chair, a drawing of a character, or a product image.',
        },
        {
          term: 'Background Removal',
          definition:
            'Sweedle automatically removes the background from your image to isolate the subject. This helps the AI focus on what matters.',
        },
      ],
      tips: [
        'Use images with a white or solid-colored background for cleanest results.',
        'Front-facing views work better than angled shots for most objects.',
        'Avoid images with multiple separate objects - the AI will try to combine them.',
        'Higher resolution images (1024x1024 or larger) produce better 3D models.',
      ],
    },
    {
      title: 'Generate from Text Tab',
      content:
        'Create an image from a text description using AI (Stable Diffusion XL). This is perfect when you have an idea but no reference image.',
      steps: [
        {
          title: 'Write Your Prompt',
          description:
            'Describe what you want to create. Be specific about the object, its features, and appearance. The more detail, the better.',
          tip: 'Example: "a wooden treasure chest with gold trim, iron hinges, ornate carvings, fantasy game style"',
        },
        {
          title: 'Select Style Preset',
          description:
            'Choose a preset that matches your intended use. Each preset optimizes the generation for specific types of game assets.',
        },
        {
          title: 'Adjust Advanced Options (Optional)',
          description:
            'Fine-tune generation with negative prompts (things to avoid), seed numbers (for reproducibility), and quality settings.',
        },
        {
          title: 'Generate and Review',
          description:
            'Click Generate to create your image. Review the result - you can regenerate with the same prompt for variations, or use it as-is.',
        },
        {
          title: 'Use the Image',
          description:
            'When satisfied, click "Use This Image" to proceed to 3D generation with your AI-created image.',
        },
      ],
      terminology: [
        {
          term: 'Prompt',
          definition:
            'A text description that tells the AI what image to generate. More detailed prompts produce more accurate results.',
          example: '"a medieval sword with silver blade and leather-wrapped handle"',
        },
        {
          term: 'Style Preset',
          definition:
            'Pre-configured settings that optimize image generation for specific use cases like characters, props, or creatures.',
        },
        {
          term: 'Negative Prompt',
          definition:
            'Things you want the AI to avoid in the generated image. Useful for preventing unwanted elements.',
          example: '"blurry, low quality, multiple objects, text, watermark"',
        },
        {
          term: 'Seed',
          definition:
            'A number that controls randomness. Using the same seed with the same prompt produces identical images.',
        },
        {
          term: 'Guidance Scale',
          definition:
            'How closely the AI follows your prompt. Higher values (7-12) follow the prompt more strictly, lower values (3-6) allow more creativity.',
        },
        {
          term: 'Inference Steps',
          definition:
            'How many refinement passes the AI makes. More steps (30-50) produce higher quality but take longer.',
        },
      ],
      tips: [
        'Be specific: "red sports car" is better than just "car".',
        'Include style keywords: "game asset style", "3D render", "clean background".',
        'Mention the viewing angle if important: "front view", "side profile", "isometric".',
        'First generation takes longer (~30-60s) while loading the AI model.',
      ],
    },
    {
      title: 'Quality Presets',
      content:
        'Choose how detailed your 3D model should be. All presets are optimized for game engines.',
      terminology: [
        {
          term: 'Draft',
          definition:
            'Fast preview quality (~30 seconds). Lower detail (~2,500 vertices) but great for quickly checking if your image will work well.',
          example: 'Use for rapid iteration when testing different source images.',
        },
        {
          term: 'Godot Ready (Recommended)',
          definition:
            'Balanced quality (~60 seconds). Medium detail (~5,000 vertices) optimized for game engines like Godot, Unity, and Unreal.',
          example: 'Best choice for most game characters and props.',
        },
        {
          term: 'Detailed',
          definition:
            'High quality (~90 seconds). Higher detail (~15,000 vertices) for hero assets that need close-up detail.',
          example: 'Use for main characters, key items, or promotional renders.',
        },
        {
          term: 'Vertices',
          definition:
            'Points in 3D space that form the mesh. More vertices = more detail but larger file size and slower rendering.',
        },
        {
          term: 'Polygons/Faces',
          definition:
            'Flat surfaces formed by connecting vertices. Game engines render these to display your 3D model.',
        },
      ],
    },
  ],

  quickStart: [
    'Drag an image into the upload area (or use Generate from Text)',
    'Enter a name for your asset',
    'Select "Godot Ready" preset for game-ready results',
    'Click "Generate 3D Mesh" to start',
  ],

  commonIssues: [
    {
      problem: 'My object looks deformed or merged',
      solution:
        'Try an image with a cleaner background or use text-to-image with "single object, centered" in your prompt.',
    },
    {
      problem: 'Text-to-image is very slow the first time',
      solution:
        'This is normal - the AI model (~7GB) needs to load into GPU memory. Subsequent generations are much faster.',
    },
    {
      problem: 'Generated image doesn\'t match my prompt',
      solution:
        'Try being more specific, adjust the guidance scale higher (8-12), or use negative prompts to exclude unwanted elements.',
    },
  ],
};

// ============================================================================
// MESH STAGE TUTORIAL
// ============================================================================

export const meshStageTutorial: StageTutorial = {
  id: 'mesh',
  stageName: 'Mesh',
  title: '3D Mesh Generation',
  introduction:
    'The AI is analyzing your image and creating a 3D mesh. This process uses Hunyuan3D-2.1 to generate the shape of your object. No action needed - just wait for the magic to happen!',

  sections: [
    {
      title: 'What\'s Happening',
      content:
        'The Hunyuan3D AI model is processing your image through several stages to create a 3D representation.',
      steps: [
        {
          title: 'Image Preprocessing',
          description:
            'Your image is prepared for the AI: background removal, resizing, and normalization.',
        },
        {
          title: 'Shape Inference',
          description:
            'The AI analyzes the image and predicts the 3D shape using deep learning. This is the main processing step.',
        },
        {
          title: 'Mesh Generation',
          description:
            'The predicted shape is converted into a polygon mesh with vertices and faces.',
        },
        {
          title: 'Mesh Optimization',
          description:
            'The raw mesh is cleaned up: removing artifacts, fixing normals, and decimating to your chosen quality level.',
        },
      ],
      terminology: [
        {
          term: 'Mesh',
          definition:
            'A 3D object made up of vertices (points), edges (lines), and faces (surfaces). This is the "skeleton" of your 3D model.',
        },
        {
          term: 'Hunyuan3D',
          definition:
            'The AI model created by Tencent that converts 2D images to 3D shapes. It\'s trained on millions of 3D objects.',
        },
        {
          term: 'Decimation',
          definition:
            'Reducing the number of polygons in a mesh while preserving its shape. Essential for game-ready assets.',
        },
        {
          term: 'Normal',
          definition:
            'A vector perpendicular to a face that tells the renderer which way the surface points. Important for lighting.',
        },
        {
          term: 'VRAM',
          definition:
            'Video RAM - memory on your GPU. The AI model requires significant VRAM (~21GB) for generation.',
        },
        {
          term: 'Inference',
          definition:
            'The process of running data through an AI model to get a prediction (in this case, a 3D shape).',
        },
      ],
      tips: [
        'Generation typically takes 30-90 seconds depending on your quality preset.',
        'You can see progress updates in the status area.',
        'If generation fails, try a different image with clearer subject.',
      ],
    },
    {
      title: 'Reviewing Your Mesh',
      content:
        'Once generation completes, you can inspect the 3D mesh in the viewer before proceeding.',
      steps: [
        {
          title: 'Rotate the View',
          description:
            'Click and drag in the 3D viewer to rotate around your model. Check all angles for issues.',
        },
        {
          title: 'Check for Problems',
          description:
            'Look for holes, missing parts, or distorted areas. Some imperfections can be fixed later.',
        },
        {
          title: 'Approve or Retry',
          description:
            'If the mesh looks good, approve to continue. If not, you can go back and try a different image.',
        },
      ],
    },
  ],

  quickStart: [
    'Wait for generation to complete (progress shown)',
    'Rotate the 3D view to inspect all angles',
    'Click "Approve & Continue" if satisfied',
    'Or go back to try a different source image',
  ],

  commonIssues: [
    {
      problem: 'Generation takes forever or hangs',
      solution:
        'Check that you have enough GPU memory. Close other GPU-intensive applications. The first run loads the 21GB model.',
    },
    {
      problem: 'Mesh has holes or missing parts',
      solution:
        'This usually means the source image was ambiguous. Try an image from a different angle or with better lighting.',
    },
    {
      problem: 'Object looks flat or squished',
      solution:
        'The AI had trouble inferring depth. Try an image that shows more 3D form, or a different viewing angle.',
    },
  ],
};

// ============================================================================
// TEXTURE STAGE TUTORIAL
// ============================================================================

export const textureStageTutorial: StageTutorial = {
  id: 'texture',
  stageName: 'Texture',
  title: 'Texture Generation',
  introduction:
    'Now we\'ll add colors and surface details to your mesh. The AI generates textures that wrap around your 3D model, bringing it to life with realistic or stylized appearances.',

  sections: [
    {
      title: 'Understanding Textures',
      content:
        'Textures are 2D images that wrap around 3D surfaces. They define how your model looks: colors, patterns, surface details, and material properties.',
      terminology: [
        {
          term: 'Texture Map',
          definition:
            'A 2D image applied to a 3D surface. Different types of maps control different visual properties.',
        },
        {
          term: 'Albedo/Diffuse Map',
          definition:
            'The base color texture without lighting effects. This is what Sweedle generates - the "paint" on your model.',
        },
        {
          term: 'UV Mapping',
          definition:
            'The process of unwrapping a 3D surface into 2D so textures can be applied. Think of it like peeling an orange and laying the peel flat.',
        },
        {
          term: 'Texture Resolution',
          definition:
            'The size of the texture image in pixels (e.g., 1024x1024). Higher resolution = more detail but larger file size.',
        },
        {
          term: 'Texel',
          definition:
            'A single pixel in a texture. Higher resolution means more texels per surface area and finer details.',
        },
      ],
    },
    {
      title: 'Texture Generation Process',
      content:
        'The AI paints your mesh based on the original source image and the 3D shape.',
      steps: [
        {
          title: 'UV Unwrapping',
          description:
            'The mesh is automatically unwrapped to create a flat UV layout for texture application.',
        },
        {
          title: 'View Synthesis',
          description:
            'The AI generates views of the textured model from multiple angles.',
        },
        {
          title: 'Texture Baking',
          description:
            'The generated views are combined and "baked" onto the UV map to create the final texture.',
        },
      ],
      tips: [
        'Texture generation requires additional VRAM. The mesh model is swapped out for the texture model.',
        'Complex models with many UV islands may take longer to texture.',
        'You can skip texturing to export a mesh-only model for external texturing.',
      ],
    },
    {
      title: 'Reviewing Your Textured Model',
      content:
        'After texturing, inspect the model to ensure colors and details look correct.',
      steps: [
        {
          title: 'Check Color Accuracy',
          description:
            'Compare the textured model to your source image. Colors should generally match.',
        },
        {
          title: 'Look for Seams',
          description:
            'Rotate the model to check for visible texture seams where UV islands meet.',
        },
        {
          title: 'Inspect Back/Hidden Areas',
          description:
            'The AI has to "guess" textures for areas not visible in the source image.',
        },
      ],
      warnings: [
        'Areas not visible in the source image may have incorrect or blurry textures.',
        'Very thin or overlapping parts may have texture bleeding issues.',
      ],
    },
  ],

  quickStart: [
    'Click "Generate Texture" to start texturing',
    'Wait for the process to complete (~30-60 seconds)',
    'Rotate and inspect the textured model',
    'Approve to continue or skip for mesh-only export',
  ],

  commonIssues: [
    {
      problem: 'Textures look blurry',
      solution:
        'This can happen with complex shapes. The texture resolution is limited. For more detail, consider manual texturing in external tools.',
    },
    {
      problem: 'Colors don\'t match the source image',
      solution:
        'The AI interprets colors based on its training. You can adjust textures in external tools like Blender after export.',
    },
    {
      problem: 'Visible seams on the model',
      solution:
        'Seams occur at UV boundaries. This is a common limitation. Professional texture artists often paint over seams manually.',
    },
  ],
};

// ============================================================================
// RIGGING STAGE TUTORIAL
// ============================================================================

export const riggingStageTutorial: StageTutorial = {
  id: 'rigging',
  stageName: 'Rigging',
  title: 'Auto-Rigging',
  introduction:
    'Rigging adds a skeleton to your model, enabling animation. Sweedle automatically detects whether your model is humanoid or quadruped and places bones accordingly.',

  sections: [
    {
      title: 'What is Rigging?',
      content:
        'Rigging is the process of adding a "skeleton" (armature) to a 3D model and defining how the mesh deforms when bones move. This is essential for animation.',
      terminology: [
        {
          term: 'Skeleton/Armature',
          definition:
            'A hierarchical structure of bones that define how a model can move. Like a puppet\'s internal framework.',
        },
        {
          term: 'Bone',
          definition:
            'A single element in a skeleton. Bones have positions, rotations, and parent-child relationships.',
        },
        {
          term: 'Joint',
          definition:
            'The point where two bones connect. Joints define where bending/rotation occurs (elbow, knee, etc.).',
        },
        {
          term: 'Weight Painting',
          definition:
            'Defines how strongly each bone influences nearby vertices. Higher weight = more influence on that area.',
        },
        {
          term: 'Skinning',
          definition:
            'The process of binding the mesh to the skeleton so they move together. Combines the skeleton with weight data.',
        },
        {
          term: 'Bind Pose / T-Pose',
          definition:
            'The default pose where the skeleton is created. Usually arms extended, legs straight. All animations are relative to this.',
        },
        {
          term: 'Humanoid',
          definition:
            'A two-legged character with arms, torso, and head. Includes humans, robots, bipedal creatures.',
        },
        {
          term: 'Quadruped',
          definition:
            'A four-legged creature like dogs, cats, horses, or fantasy beasts.',
        },
      ],
    },
    {
      title: 'Character Type Detection',
      content:
        'Sweedle analyzes your model\'s shape to determine the best skeleton type.',
      steps: [
        {
          title: 'Auto-Detection',
          description:
            'The AI examines your mesh and predicts whether it\'s humanoid or quadruped based on proportions and shape.',
        },
        {
          title: 'Manual Override',
          description:
            'If auto-detection is wrong, you can manually select the character type before rigging.',
        },
      ],
      tips: [
        'Humanoid skeletons have 65 bones including fingers.',
        'Quadruped skeletons have 45 bones including tail.',
        'Non-character objects (props, vehicles) should skip rigging.',
      ],
    },
    {
      title: 'Rigging Process',
      content:
        'The auto-rigging system places bones and calculates weights automatically.',
      steps: [
        {
          title: 'Skeleton Placement',
          description:
            'Bones are positioned inside the mesh based on the detected shape. Key joints are aligned with expected anatomy.',
        },
        {
          title: 'Weight Calculation',
          description:
            'Each vertex is assigned influence weights for nearby bones. This determines how the mesh deforms.',
        },
        {
          title: 'Quality Check',
          description:
            'The system validates bone positions and weight distributions to ensure animation will work correctly.',
        },
      ],
      terminology: [
        {
          term: 'Root Bone',
          definition:
            'The top-level bone in the hierarchy (usually "Hips"). All other bones are children of this bone.',
        },
        {
          term: 'Bone Hierarchy',
          definition:
            'The parent-child relationships between bones. Moving a parent bone moves all its children.',
          example: 'Spine → Chest → Shoulder → Upper Arm → Lower Arm → Hand → Fingers',
        },
        {
          term: 'Vertex Weights',
          definition:
            'Numbers (0-1) defining how much each bone affects each vertex. Weights for each vertex sum to 1.',
        },
        {
          term: 'Max Influences',
          definition:
            'Maximum number of bones that can affect a single vertex. Sweedle uses 4 (standard for games).',
        },
      ],
    },
    {
      title: 'Skeleton Visualization',
      content:
        'After rigging, you can view the skeleton overlaid on your model.',
      steps: [
        {
          title: 'Toggle Skeleton View',
          description:
            'Use the skeleton button in the viewer toolbar to show/hide bones.',
        },
        {
          title: 'Inspect Bone Placement',
          description:
            'Check that major joints (shoulders, elbows, knees) are positioned correctly.',
        },
        {
          title: 'Select Bones',
          description:
            'Click on bones to see their names and positions. This helps verify the rigging.',
        },
      ],
    },
  ],

  quickStart: [
    'Review detected character type (humanoid/quadruped)',
    'Click "Start Auto-Rigging" to begin',
    'Wait for bone placement and weight calculation',
    'Toggle skeleton view to inspect results',
    'Approve to continue to animation',
  ],

  commonIssues: [
    {
      problem: 'Wrong character type detected',
      solution:
        'Manually select the correct type before rigging. If your model is unusual, try the closest match.',
    },
    {
      problem: 'Bones are misaligned',
      solution:
        'This can happen with non-standard proportions. For best results, ensure models have clear anatomy.',
    },
    {
      problem: 'Model is not animatable (props, vehicles)',
      solution:
        'Skip the rigging stage for non-character assets. These don\'t need skeletons.',
    },
  ],
};

// ============================================================================
// ANIMATION STAGE TUTORIAL
// ============================================================================

export const animationStageTutorial: StageTutorial = {
  id: 'animation',
  stageName: 'Animation',
  title: 'Animation',
  introduction:
    'Bring your rigged model to life with animations! Choose from built-in presets or import professional animations from Mixamo.',

  sections: [
    {
      title: 'Preset Library Tab',
      content:
        'Choose from procedurally generated animations optimized for your character type.',
      steps: [
        {
          title: 'Browse Presets',
          description:
            'View available animations for your character type (humanoid or quadruped).',
        },
        {
          title: 'Select an Animation',
          description:
            'Click on an animation preset to see its description and configure parameters.',
        },
        {
          title: 'Adjust Parameters',
          description:
            'Fine-tune the animation speed, intensity, and blend factor to match your needs.',
        },
        {
          title: 'Apply Animation',
          description:
            'Click "Apply Animation" to add it to your model. You can add multiple animations.',
        },
      ],
      terminology: [
        {
          term: 'Animation Preset',
          definition:
            'A pre-made animation type (idle, walk, run, attack) that generates keyframes for your specific skeleton.',
        },
        {
          term: 'Procedural Animation',
          definition:
            'Animation generated by code/algorithms rather than hand-animated. Adapts to any skeleton that has the required bones.',
        },
        {
          term: 'Speed',
          definition:
            'How fast the animation plays. 1.0 is normal speed, 2.0 is twice as fast, 0.5 is half speed.',
        },
        {
          term: 'Intensity',
          definition:
            'How pronounced the movements are. Higher intensity = more exaggerated motion.',
        },
        {
          term: 'Blend Factor',
          definition:
            'How much of the animation to apply vs. the base pose. Used for mixing animations together.',
        },
        {
          term: 'Loop Mode',
          definition:
            'How the animation repeats: "Loop" plays continuously, "Once" plays and stops, "Ping-Pong" plays forward then backward.',
        },
      ],
      tips: [
        'Start with "Idle" animation - it\'s subtle and works for any situation.',
        'Walk and Run are great for locomotion in games.',
        'You can apply multiple animations - they\'ll be exported together.',
        'Quadrupeds have special animations like Trot and Tail Wag.',
      ],
    },
    {
      title: 'Import Mixamo Tab',
      content:
        'Import professional motion-captured animations from Adobe Mixamo for higher quality results.',
      steps: [
        {
          title: 'Get Animations from Mixamo',
          description:
            'Visit mixamo.com (free), browse their animation library, and download as FBX format.',
        },
        {
          title: 'Download Settings',
          description:
            'When downloading, select "FBX" format and "Without Skin" option for animation-only export.',
        },
        {
          title: 'Upload FBX',
          description:
            'Drag and drop your downloaded FBX file into the upload area.',
        },
        {
          title: 'Review Validation',
          description:
            'Sweedle validates the animation and shows bone coverage - how many bones matched your skeleton.',
        },
        {
          title: 'Import Animation',
          description:
            'If validation passes, click "Import Animation" to add it to your model.',
        },
      ],
      terminology: [
        {
          term: 'Mixamo',
          definition:
            'A free Adobe service with thousands of professional motion-captured animations for 3D characters.',
        },
        {
          term: 'FBX',
          definition:
            'A 3D file format that can contain models, skeletons, and animations. Industry standard for game assets.',
        },
        {
          term: 'Retargeting',
          definition:
            'Adapting an animation made for one skeleton to work with a different skeleton. Sweedle does this automatically.',
        },
        {
          term: 'Bone Mapping',
          definition:
            'Matching bone names between different skeletons. Mixamo uses "mixamorig:" prefix, Sweedle maps these to standard names.',
        },
        {
          term: 'Bone Coverage',
          definition:
            'Percentage of source animation bones that matched target skeleton bones. Higher is better (aim for 80%+).',
        },
        {
          term: 'Without Skin',
          definition:
            'Mixamo export option that includes only the animation data, not the character mesh. This is what Sweedle needs.',
        },
      ],
      tips: [
        'Download Mixamo animations with "Without Skin" to get just the animation.',
        '80%+ bone coverage is good for most animations.',
        'Some finger animations may not transfer if your model lacks finger bones.',
        'Mixamo has categories: Locomotion, Combat, Dancing, etc.',
      ],
      warnings: [
        'Mixamo animations are designed for humanoid characters only.',
        'Very stylized or non-standard proportions may have animation issues.',
        'First Mixamo import parses the FBX using Blender (requires Blender installed).',
      ],
    },
    {
      title: 'Animation Timeline',
      content:
        'Control playback and preview your animations in the viewer.',
      steps: [
        {
          title: 'Play/Pause',
          description:
            'Use the play button to preview animations on your model in real-time.',
        },
        {
          title: 'Scrub Timeline',
          description:
            'Drag the playhead to preview specific frames of the animation.',
        },
        {
          title: 'Select Animation',
          description:
            'If you have multiple animations, select which one to preview from your applied list.',
        },
      ],
      terminology: [
        {
          term: 'Keyframe',
          definition:
            'A saved pose at a specific time. Animation interpolates between keyframes to create smooth motion.',
        },
        {
          term: 'Frame Rate (FPS)',
          definition:
            'Frames Per Second - how many poses per second. 30 FPS is standard for game animations.',
        },
        {
          term: 'Duration',
          definition:
            'Total length of the animation in seconds. Looping animations often have seamless start/end poses.',
        },
        {
          term: 'Interpolation',
          definition:
            'How the animation transitions between keyframes. Linear is even, ease-in/out is smooth.',
        },
      ],
    },
  ],

  quickStart: [
    'Choose source: Preset Library or Import Mixamo',
    'For presets: Select type, adjust parameters, click Apply',
    'For Mixamo: Upload FBX, verify coverage, click Import',
    'Use timeline to preview animations',
    'Add multiple animations if needed',
    'Approve to continue to export',
  ],

  commonIssues: [
    {
      problem: 'Preset animation looks wrong on my model',
      solution:
        'Try adjusting intensity lower. Some models with unusual proportions may need parameter tweaking.',
    },
    {
      problem: 'Mixamo animation has missing bone movements',
      solution:
        'Check bone coverage percentage. If below 80%, some bones couldn\'t be mapped. This is normal for simplified skeletons.',
    },
    {
      problem: 'Animation plays too fast or slow',
      solution:
        'Adjust the Speed parameter. Default is 1.0, try values between 0.5 and 2.0.',
    },
  ],
};

// ============================================================================
// EXPORT STAGE TUTORIAL
// ============================================================================

export const exportStageTutorial: StageTutorial = {
  id: 'export',
  stageName: 'Export',
  title: 'Export',
  introduction:
    'Your asset is ready! Export it in the format you need for your game engine or 3D software. All exports are optimized for real-time rendering.',

  sections: [
    {
      title: 'Export Formats',
      content:
        'Choose the file format that works best with your target platform.',
      terminology: [
        {
          term: 'GLB (Recommended)',
          definition:
            'Binary glTF format. Single file containing mesh, textures, skeleton, and animations. Supported by all major game engines.',
          example: 'Best for Godot, Unity, Unreal, Three.js, Babylon.js',
        },
        {
          term: 'glTF',
          definition:
            'Text-based version of GLB. Separate files for mesh and textures. Useful for debugging or manual editing.',
        },
        {
          term: 'FBX',
          definition:
            'Autodesk format. Industry standard for 3D software interchange. Good for Blender, Maya, 3ds Max workflows.',
        },
        {
          term: 'OBJ',
          definition:
            'Simple mesh format. No skeleton or animations. Good for static props or when you only need geometry.',
        },
      ],
    },
    {
      title: 'Export Options',
      content:
        'Configure how your asset is exported.',
      steps: [
        {
          title: 'Select Format',
          description:
            'Choose GLB for most use cases. Use FBX if your workflow requires it.',
        },
        {
          title: 'Choose Engine Preset (Optional)',
          description:
            'Select your target engine for optimized coordinate systems and settings.',
        },
        {
          title: 'Select Animations',
          description:
            'Choose which animations to include in the export. All are included by default.',
        },
        {
          title: 'Download',
          description:
            'Click export to download your file. It\'s also saved to your asset library.',
        },
      ],
      terminology: [
        {
          term: 'Engine Preset',
          definition:
            'Pre-configured export settings for specific game engines. Handles coordinate system differences.',
        },
        {
          term: 'Coordinate System',
          definition:
            'Which direction is "up" and how axes are oriented. Engines differ: Unity uses Y-up, Blender uses Z-up.',
        },
        {
          term: 'Embedded Textures',
          definition:
            'Textures included inside the file (GLB) vs. separate image files. Embedded is more portable.',
        },
        {
          term: 'Embedded Animations',
          definition:
            'Animations included inside the model file. All your applied animations will be embedded.',
        },
      ],
    },
    {
      title: 'Engine-Specific Notes',
      content:
        'Tips for importing into popular game engines.',
      tips: [
        'Godot 4: Import GLB directly. Animations appear in the AnimationPlayer.',
        'Unity: Import GLB or FBX. Check "Import Animation" in import settings.',
        'Unreal: Use FBX for best results. GLB works via glTF importer plugin.',
        'Blender: Import GLB or FBX. Animations appear in the Action Editor.',
      ],
    },
    {
      title: 'What\'s Included',
      content:
        'Summary of what your exported file contains.',
      terminology: [
        {
          term: 'Mesh',
          definition:
            'The 3D geometry (vertices, faces) of your model.',
        },
        {
          term: 'Materials',
          definition:
            'Surface properties like color, texture references, and shader settings.',
        },
        {
          term: 'Textures',
          definition:
            'The color/albedo map generated for your model (if textured).',
        },
        {
          term: 'Skeleton',
          definition:
            'The bone hierarchy for animation (if rigged).',
        },
        {
          term: 'Animations',
          definition:
            'All applied animation clips with their keyframe data.',
        },
        {
          term: 'LODs',
          definition:
            'Level of Detail meshes at different polygon counts (if generated).',
        },
      ],
    },
  ],

  quickStart: [
    'Select export format (GLB recommended)',
    'Choose engine preset if applicable',
    'Select which animations to include',
    'Click "Export" to download',
    'Import into your game engine',
  ],

  commonIssues: [
    {
      problem: 'Model appears tiny/huge in game engine',
      solution:
        'Sweedle exports in meters. Unity: 1 unit = 1 meter. Godot: May need scale adjustment in import settings.',
    },
    {
      problem: 'Textures don\'t appear in engine',
      solution:
        'Use GLB format which embeds textures. For separate files, ensure texture paths are correct.',
    },
    {
      problem: 'Animations not showing in engine',
      solution:
        'Check that animations were applied before export. In engine, look for AnimationPlayer (Godot) or Animation tab (Unity).',
    },
  ],
};

// ============================================================================
// EXPORT ALL TUTORIALS
// ============================================================================

export const allTutorials: Record<string, StageTutorial> = {
  upload: uploadStageTutorial,
  mesh: meshStageTutorial,
  texture: textureStageTutorial,
  rigging: riggingStageTutorial,
  animation: animationStageTutorial,
  export: exportStageTutorial,
};

export function getTutorialForStage(stageId: string): StageTutorial | undefined {
  return allTutorials[stageId];
}

// Glossary of all terms across all tutorials
export function getAllTerminology(): TermDefinition[] {
  const terms: TermDefinition[] = [];
  const seen = new Set<string>();

  Object.values(allTutorials).forEach((tutorial) => {
    tutorial.sections.forEach((section) => {
      section.terminology?.forEach((term) => {
        if (!seen.has(term.term.toLowerCase())) {
          seen.add(term.term.toLowerCase());
          terms.push(term);
        }
      });
    });
  });

  return terms.sort((a, b) => a.term.localeCompare(b.term));
}
