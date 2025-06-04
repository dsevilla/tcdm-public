package cursohadoop.wordcount;

import java.io.IOException;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import org.apache.hadoop.io.LongWritable;
import org.apache.hadoop.io.Text;
import org.apache.hadoop.mapreduce.Mapper;

public class WordCountMapper extends Mapper<LongWritable, Text, Text, LongWritable>
{
    @Override
    public void map(LongWritable key, Text value, Context ctxt) throws IOException, InterruptedException
    {
        Matcher matcher = pat.matcher(value.toString());
        while (matcher.find())
        {
            word.set(matcher.group().toLowerCase());
            ctxt.write(word, one);
        }
    }

    private Text word = new Text();
    private final static LongWritable one = new LongWritable(1);
    private Pattern pat = Pattern.compile("\\b[a-zA-Z\\u00c0-\\uFFFF]+\\b");
}
