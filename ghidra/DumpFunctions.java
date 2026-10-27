// Ghidra post-analysis script; produces a bounded JSON report.
//@category DeviceRE
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.program.model.listing.Function;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.Iterator;

public class DumpFunctions extends GhidraScript {
  String escape(String s) {
    return s.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t");
  }
  public void run() throws Exception {
    String[] args=getScriptArgs();
    if (args.length<1) return;
    StringBuilder b=new StringBuilder();
    b.append("{\"program\":\"").append(escape(currentProgram.getName())).append("\",\"functions\":[");
    Iterator<Function> it=currentProgram.getFunctionManager().getFunctions(true);
    DecompInterface dec=new DecompInterface();dec.openProgram(currentProgram);
    int count=0;
    while(it.hasNext() && count<100) {
      Function f=it.next();if(count>0)b.append(',');
      b.append("{\"name\":\"").append(escape(f.getName()))
        .append("\",\"address\":\"").append(f.getEntryPoint()).append("\"");
      if(count<20) {
        DecompileResults r=dec.decompileFunction(f,20,monitor);
        if(r.decompileCompleted() && r.getDecompiledFunction()!=null)
          b.append(",\"decompiled\":\"").append(escape(r.getDecompiledFunction().getC().substring(0,Math.min(4000,r.getDecompiledFunction().getC().length())))).append("\"");
      }
      b.append('}');count++;
    }
    dec.dispose();b.append("],\"function_limit\":100}");
    Files.write(Paths.get(args[0]),b.toString().getBytes(StandardCharsets.UTF_8));
  }
}
