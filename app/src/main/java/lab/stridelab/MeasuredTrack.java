package lab.stridelab;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.TimeZone;
import java.io.ByteArrayOutputStream;
import java.nio.charset.StandardCharsets;

/** Foreground measured track. Only the native location listener supplies fixes.
 * No synthetic session, editable map node or user-selected time is accepted here. */
final class MeasuredTrack {
 static final long EPOCH=631065600L;
 static final int LIMIT=18000;
 static final class Fix {
  final long utc; final double lat,lon,dist;
  Fix(long utc,double lat,double lon,double dist){this.utc=utc;this.lat=lat;this.lon=lon;this.dist=dist;}
 }
 private final List<Fix> fixes=new ArrayList<>();
 boolean recording=false;
 void start(){fixes.clear();recording=true;}
 void stop(){recording=false;}
 int size(){return fixes.size();}
 double distance(){return fixes.isEmpty()?0:fixes.get(fixes.size()-1).dist;}
 long duration(){return fixes.size()<2?0:fixes.get(fixes.size()-1).utc-fixes.get(0).utc;}
 List<Fix> snapshot(){return new ArrayList<>(fixes);}
 static double distance(Fix a,double lat,double lon){
  double r=Math.PI/180,dlat=(lat-a.lat)*r,dlon=(lon-a.lon)*r;
  double h=Math.pow(Math.sin(dlat/2),2)+Math.cos(a.lat*r)*Math.cos(lat*r)*Math.pow(Math.sin(dlon/2),2);
  return 6371008.8*2*Math.asin(Math.sqrt(Math.max(0,Math.min(1,h))));
 }
 boolean add(long utc,double lat,double lon){
  if(!recording||size()>=LIMIT||utc<EPOCH||utc-EPOCH>=0xffffffffL||!Double.isFinite(lat)||!Double.isFinite(lon)||Math.abs(lat)>90||lon< -180||lon>=180)return false;
  Fix prev=size()==0?null:fixes.get(size()-1);
  if(prev!=null&&utc<=prev.utc)return false;
  double d=prev==null?0:prev.dist+distance(prev,lat,lon);
  if(!Double.isFinite(d)||d>=42949672.95)return false;
  fixes.add(new Fix(utc,lat,lon,d));
  if(size()>=LIMIT)stop();
  return true;
 }
 private void check(){if(recording||size()<2||duration()<1||duration()>=4294967L)throw new IllegalStateException("请结束记录并确认至少有两个有效定位点");}
 private static String iso(long t){SimpleDateFormat f=new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'",Locale.US);f.setTimeZone(TimeZone.getTimeZone("UTC"));return f.format(new Date(t*1000));}
 private static String num(double x){return String.format(Locale.US,"%.7f",x);}
 byte[] tcx(){
  check();StringBuilder b=new StringBuilder();
  b.append("<?xml version=\"1.0\" encoding=\"UTF-8\"?><TrainingCenterDatabase xmlns=\"http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2\"><Activities><Activity Sport=\"Running\"><Id>").append(iso(fixes.get(0).utc)).append("</Id><Lap StartTime=\"").append(iso(fixes.get(0).utc)).append("\"><TotalTimeSeconds>").append(duration()).append("</TotalTimeSeconds><DistanceMeters>").append(num(distance())).append("</DistanceMeters><Calories>0</Calories><Intensity>Active</Intensity><TriggerMethod>Manual</TriggerMethod><Track>");
  for(Fix f:fixes)b.append("<Trackpoint><Time>").append(iso(f.utc)).append("</Time><Position><LatitudeDegrees>").append(num(f.lat)).append("</LatitudeDegrees><LongitudeDegrees>").append(num(f.lon)).append("</LongitudeDegrees></Position><DistanceMeters>").append(num(f.dist)).append("</DistanceMeters></Trackpoint>");
  b.append("</Track><Notes>Device GPS fixes; distance from recorded positions; calories and physiological metrics unavailable.</Notes></Lap><Notes>StrideLab foreground device GPS recording.</Notes></Activity></Activities></TrainingCenterDatabase>");
  return b.toString().getBytes(StandardCharsets.UTF_8);
 }
 static void put(ByteArrayOutputStream b,long v,int n){for(int i=0;i<n;i++)b.write((int)(v>>>(8*i))&255);}
 static int crc(byte[] b){int c=0;for(byte v:b){c^=v&255;for(int i=0;i<8;i++)c=(c&1)!=0?(c>>>1)^0xa001:c>>>1;}return c;}
 static void def(ByteArrayOutputStream b,int local,int global,int[][] fields){b.write(64|local);b.write(0);b.write(0);put(b,global,2);b.write(fields.length);for(int[] f:fields){b.write(f[0]);b.write(f[1]);b.write(f[2]);}}
 static void msg(ByteArrayOutputStream b,int local,int[][] fields,long... values){if(fields.length!=values.length)throw new IllegalArgumentException("FIT fields");b.write(local);for(int i=0;i<values.length;i++)put(b,values[i],fields[i][1]);}
 static long semi(double deg){return Math.min(2147483646L,Math.round(deg*2147483648.0/180));}
 byte[] fit(){
  check();ByteArrayOutputStream d=new ByteArrayOutputStream();
  long t0=fixes.get(0).utc-EPOCH,t1=fixes.get(size()-1).utc-EPOCH,ms=duration()*1000,cm=Math.round(distance()*100);
  int[][] id={{0,1,0},{1,2,132},{4,4,134}};
  int[][] event={{253,4,134},{0,1,0},{1,1,0}};
  int[][] rec={{253,4,134},{0,4,133},{1,4,133},{5,4,134}};
  int[][] lap={{254,2,132},{253,4,134},{0,1,0},{1,1,0},{2,4,134},{7,4,134},{8,4,134},{9,4,134},{25,1,0}};
  int[][] session={{254,2,132},{253,4,134},{0,1,0},{1,1,0},{2,4,134},{5,1,0},{6,1,0},{7,4,134},{8,4,134},{9,4,134},{25,2,132},{26,2,132}};
  int[][] activity={{253,4,134},{0,4,134},{1,2,132},{2,1,0},{3,1,0},{4,1,0}};
  def(d,0,0,id);msg(d,0,id,4,255,t0);
  def(d,1,21,event);msg(d,1,event,t0,0,0);
  def(d,2,20,rec);for(Fix f:fixes)msg(d,2,rec,f.utc-EPOCH,semi(f.lat),semi(f.lon),Math.round(f.dist*100));
  msg(d,1,event,t1,0,4);
  def(d,3,19,lap);msg(d,3,lap,0,t1,9,1,t0,ms,ms,cm,1);
  def(d,4,18,session);msg(d,4,session,0,t1,8,1,t0,1,0,ms,ms,cm,0,1);
  def(d,5,34,activity);msg(d,5,activity,t1,ms,1,0,26,1);
  ByteArrayOutputStream out=new ByteArrayOutputStream();out.write(14);out.write(32);put(out,2100,2);put(out,d.size(),4);for(byte v:new byte[]{46,70,73,84})out.write(v);put(out,crc(out.toByteArray()),2);byte[] body=d.toByteArray();out.write(body,0,body.length);put(out,crc(out.toByteArray()),2);return out.toByteArray();
 }
}
