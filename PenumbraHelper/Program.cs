using LiteDB;
using System.Text.Json;
using System.Text.RegularExpressions;
using JsonSerializer = System.Text.Json.JsonSerializer;

string dbPath = @"C:\Users\herme\AppData\Roaming\XIVLauncher\pluginConfigs\Penumbra\mod_data.db";
string orgFile = @"C:\Users\herme\AppData\Roaming\XIVLauncher\pluginConfigs\Penumbra\mod_filesystem\organization.json";

var action = args.Length > 0 ? args[0] : "help";

switch (action)
{
    case "list":
        ListMods();
        break;
    case "set-folder":
        if (args.Length < 3) { Console.Error.WriteLine("Usage: set-folder <mod-identifier> <folder-path>"); return; }
        SetFolder(args[1], args[2]);
        break;
    case "create-folders":
        CreateFolders(args.Length > 1 ? args[1] : null);
        break;
    case "set-default-import":
        SetDefaultImport(args.Length > 1 ? args[1] : "");
        break;
    case "delete-all":
        DeleteAll();
        break;
    case "delete":
        if (args.Length < 2) { Console.Error.WriteLine("Usage: delete <mod-identifier>"); return; }
        Delete(args[1]);
        break;
    case "purge-orphans":
        PurgeOrphans();
        break;
    default:
        Console.WriteLine("Commands:");
        Console.WriteLine("  list                 - List all mods with their folder");
        Console.WriteLine("  set-folder <id> <p>  - Set mod's folder path");
        Console.WriteLine("  create-folders [f]    - Create folder structure (from JSON file or default)");
        Console.WriteLine("  set-default-import <p> - Set default import folder (empty = none)");
        Console.WriteLine("  delete-all            - Delete ALL mods from database");
        Console.WriteLine("  delete <id>           - Delete a single mod");
        Console.WriteLine("  purge-orphans         - Remove DB entries for mods with no files");
        break;
}

void ListMods()
{
    try
    {
        using var db = new LiteDatabase($"Filename={dbPath};Connection=Shared;Timeout=00:00:05");
        var collection = db.GetCollection("LocalModData");
        var all = collection.FindAll().ToList();
        Console.WriteLine($"Total mods: {all.Count}");
        Console.WriteLine();
        foreach (var doc in all.OrderBy(d => d["Folder"].AsString).ThenBy(d => d["_id"].AsString))
        {
            var id = doc["_id"].AsString;
            var folder = doc["Folder"].AsString;
            Console.WriteLine($"  {(string.IsNullOrEmpty(folder) ? "(root)" : folder),-25} {id}");
        }
    }
    catch (Exception ex)
    {
        Console.Error.WriteLine($"Error: {ex.Message}");
    }
}

void SetFolder(string modId, string folderPath)
{
    try
    {
        using var db = new LiteDatabase($"Filename={dbPath};Connection=Shared;Timeout=00:00:05");
        var collection = db.GetCollection("LocalModData");

        // Try exact match or partial match
        var mod = collection.FindById(new BsonValue(modId));
        
        if (mod == null)
        {
            // Try fuzzy match
            var all = collection.FindAll();
            mod = all.FirstOrDefault(d => d["_id"].AsString.StartsWith(modId, StringComparison.OrdinalIgnoreCase));
        }

        if (mod == null)
        {
            Console.Error.WriteLine($"Mod '{modId}' not found. Use 'list' to see available mods.");
            return;
        }

        var actualId = mod["_id"].AsString;
        mod["Folder"] = folderPath;
        collection.Update(mod);
        Console.WriteLine($"✅ '{actualId}' → Folder: \"{folderPath}\"");
    }
    catch (Exception ex)
    {
        Console.Error.WriteLine($"Error: {ex.Message}");
    }
}

void DeleteAll()
{
    Console.Write($"This will DELETE ALL {dbPath} mods. ARE YOU SURE? (yes/no): ");
    var confirm = Console.ReadLine();
    if (confirm?.ToLower() != "yes") { Console.WriteLine("Cancelled."); return; }
    
    try
    {
        using var db = new LiteDatabase($"Filename={dbPath};Connection=Shared;Timeout=00:00:05");
        var collection = db.GetCollection("LocalModData");
        var count = collection.Count();
        collection.DeleteAll();
        Console.WriteLine($"✅ Deleted {count} mods from database.");
    }
    catch (Exception ex)
    {
        Console.Error.WriteLine($"Error: {ex.Message}");
    }
}

void Delete(string modId)
{
    try
    {
        using var db = new LiteDatabase($"Filename={dbPath};Connection=Shared;Timeout=00:00:05");
        var collection = db.GetCollection("LocalModData");

        // Try exact match or partial match
        var mod = collection.FindById(new BsonValue(modId));
        
        if (mod == null)
        {
            var all = collection.FindAll();
            mod = all.FirstOrDefault(d => d["_id"].AsString.StartsWith(modId, StringComparison.OrdinalIgnoreCase));
        }

        if (mod == null)
        {
            Console.Error.WriteLine($"Mod '{modId}' not found.");
            return;
        }

        var actualId = mod["_id"].AsString;
        collection.Delete(mod["_id"]);
        Console.WriteLine($"✅ Deleted: '{actualId}'");
    }
    catch (Exception ex)
    {
        Console.Error.WriteLine($"Error: {ex.Message}");
    }
}

void PurgeOrphans()
{
    try
    {
        using var db = new LiteDatabase($"Filename={dbPath};Connection=Shared;Timeout=00:00:05");
        var collection = db.GetCollection("LocalModData");
        var all = collection.FindAll().ToList();
        var penumbraDir = @"D:\penumbramods";
        
        int purged = 0;
        foreach (var doc in all)
        {
            var id = doc["_id"].AsString;
            var modDir = Path.Combine(penumbraDir, id);
            if (!Directory.Exists(modDir))
            {
                collection.Delete(doc["_id"]);
                Console.WriteLine($"  🗑️ Purged orphan: '{id}'");
                purged++;
            }
        }
        Console.WriteLine($"✅ Purged {purged} orphan entries (no mod directory).");
    }
    catch (Exception ex)
    {
        Console.Error.WriteLine($"Error: {ex.Message}");
    }
}

void CreateFolders(string? jsonFile)
{
    // Build folder tree from paths (split "/" for proper nesting)
    var folderDict = new Dictionary<string, object?>();
    
    string[] folderTree;
    if (jsonFile != null && File.Exists(jsonFile))
    {
        folderTree = JsonSerializer.Deserialize<string[]>(File.ReadAllText(jsonFile))!;
    }
    else
    {
        folderTree = new[]
        {
            "Body",
            "Body/Heliosphere",
            "VFX",
            "VFX/Jobs",
            "VFX/Jobs/PLD", "VFX/Jobs/WAR", "VFX/Jobs/DRK", "VFX/Jobs/GNB",
            "VFX/Jobs/WHM", "VFX/Jobs/SCH", "VFX/Jobs/AST", "VFX/Jobs/SGE",
            "VFX/Jobs/MNK", "VFX/Jobs/DRG", "VFX/Jobs/NIN", "VFX/Jobs/SAM",
            "VFX/Jobs/RPR", "VFX/Jobs/VPR",
            "VFX/Jobs/BRD", "VFX/Jobs/MCH", "VFX/Jobs/DNC",
            "VFX/Jobs/BLM", "VFX/Jobs/SMN", "VFX/Jobs/RDM", "VFX/Jobs/PCT",
            "VFX/Jobs/BLU",
            "Gear",
            "Gear/Sets",
            "Gear/Slots",
            "Gear/Slots/Head", "Gear/Slots/Chest", "Gear/Slots/Hands",
            "Gear/Slots/Legs", "Gear/Slots/Feet",
            "Gear/Slots/Ears", "Gear/Slots/Neck", "Gear/Slots/Wrists", "Gear/Slots/Rings",
            "Gear/Weapons",
            "Gear/Weapons/PLD", "Gear/Weapons/WAR", "Gear/Weapons/DRK", "Gear/Weapons/GNB",
            "Gear/Weapons/WHM", "Gear/Weapons/SCH", "Gear/Weapons/AST", "Gear/Weapons/SGE",
            "Gear/Weapons/MNK", "Gear/Weapons/DRG", "Gear/Weapons/NIN", "Gear/Weapons/SAM",
            "Gear/Weapons/RPR", "Gear/Weapons/VPR",
            "Gear/Weapons/BRD", "Gear/Weapons/MCH", "Gear/Weapons/DNC",
            "Gear/Weapons/BLM", "Gear/Weapons/SMN", "Gear/Weapons/RDM", "Gear/Weapons/PCT",
            "Gear/Weapons/BLU",
            "UI",
            "Animation",
            "Hair",
            "Face",
            "Sculpt",
            "Makeup",
            "Tattoos",
            "Misc"
        };
    }

    // Build nested dict from paths
    foreach (var path in folderTree)
    {
        var parts = path.Split('/', StringSplitOptions.RemoveEmptyEntries);
        var current = folderDict;
        for (int i = 0; i < parts.Length; i++)
        {
            var name = parts[i];
            if (!current.ContainsKey(name))
                current[name] = new Dictionary<string, object?>();
            
            if (i < parts.Length - 1 && current[name] is Dictionary<string, object?> next)
                current = next;
        }
    }

    // Serialize
    var newOrg = new Dictionary<string, object?>
    {
        ["Version"] = 1,
        ["Folders"] = folderDict,
        ["Separators"] = new Dictionary<string, object?>()
    };

    var json = JsonSerializer.Serialize(newOrg, new JsonSerializerOptions 
    { 
        WriteIndented = true,
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase
    });
    
    File.WriteAllText(orgFile, json);
    Console.WriteLine($"✅ Folder structure created with {folderTree.Length} folders");
}

void SetDefaultImport(string folder)
{
    var configFile = @"C:\Users\herme\AppData\Roaming\XIVLauncher\pluginConfigs\Penumbra\ui_config.json";
    if (File.Exists(configFile))
    {
        var config = JsonSerializer.Deserialize<Dictionary<string, object?>>(File.ReadAllText(configFile))!;
        config["DefaultImportFolder"] = folder;
        File.WriteAllText(configFile, JsonSerializer.Serialize(config, new JsonSerializerOptions { WriteIndented = true }));
        Console.WriteLine($"✅ Default import folder set to: \"{(string.IsNullOrEmpty(folder) ? "(none)" : folder)}\"");
    }
}
